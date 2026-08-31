"""The routes the ingestion worker calls.

Two of them, both machine-to-machine, both behind a shared secret that is not a
user credential. "Internal" describes who is expected to call, not whether the
caller is checked — an unauthenticated endpoint that mutates document state is
an unauthenticated endpoint whatever the network diagram says.

The report handler is the only way the worker can change anything in this
database. Everything it is told is verified against what is already stored
before a single field is written: a caller holding a job id is not thereby
trusted about which document that job belongs to, and a message that arrives
late or twice must not undo work that has moved on.
"""

from __future__ import annotations

import hmac
import logging

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from ..selectors import documents as document_selectors
from ..services import job_service
from .serializers import IngestionReportSerializer

log = logging.getLogger(__name__)

TOKEN_HEADER = "X-Internal-Token"


class IsIngestionWorker(BasePermission):
    """The shared secret between Django and the ai_service worker.

    Compared in constant time. A naive ``==`` on a secret leaks its prefix
    through timing, which is a slow but real way to recover one.

    An unset token denies everything rather than allowing everything: a
    deployment that forgets to configure this should stop working loudly, not
    open its document pipeline to anyone who can reach the port.
    """

    message = "Invalid or missing internal token."

    def has_permission(self, request, view) -> bool:
        expected = getattr(settings, "AI_SERVICE_INTERNAL_TOKEN", "") or ""
        if not expected:
            log.error("AI_SERVICE_INTERNAL_TOKEN is not configured; refusing internal request")
            return False

        presented = request.headers.get(TOKEN_HEADER, "")
        if not presented:
            return False
        return hmac.compare_digest(presented, expected)


@api_view(["POST"])
@authentication_classes([])  # a service, not a user — no session, no JWT
@permission_classes([IsIngestionWorker])
def ingestion_report(request):
    """Record one stage transition reported by the worker.

    Returns 200 for anything successfully applied *and* for anything correctly
    ignored, because both mean "we are in agreement now" and the worker should
    not retry either. A 4xx here is reserved for a message that does not
    describe a real job.
    """
    form = IngestionReportSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    data = form.validated_data

    job = job_service.locate_job(
        job_id=data["job_id"],
        document_id=data["document_id"],
        document_version_id=data["document_version_id"],
    )
    if job is None:
        # Deliberately the same answer for "no such job" and "those three ids do
        # not belong together": a caller probing the endpoint learns nothing
        # about which of its guesses was closer.
        log.warning(
            "ingestion report did not match any job",
            extra={"job_id": str(data["job_id"])},
        )
        return Response(
            {"detail": "No ingestion job matches that report."},
            status=status.HTTP_404_NOT_FOUND,
        )

    outcome = job_service.apply_report(job, data)
    log.info(
        "ingestion report applied",
        extra={
            "job_id": str(job.id),
            "stage": data["stage"],
            "outcome": outcome.action,
        },
    )
    return Response(
        {
            "applied": outcome.applied,
            "action": outcome.action,
            "job_status": job.status,
            "document_status": job.document.status,
        }
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([IsIngestionWorker])
def document_file(request):
    """Serve the bytes behind a stored file reference.

    This is what lets the worker run anywhere — a different container, a
    different host — without the two services having to share a filesystem.

    The reference is not taken on trust. It is checked against the
    DocumentVersion rows that actually exist, so this cannot be used to read an
    arbitrary path under MEDIA_ROOT: only files this app put there, named by a
    version it created.
    """
    reference = request.query_params.get("reference", "")
    if not reference:
        return Response(
            {"detail": "reference is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    version = document_selectors.version_by_file(reference)
    if version is None:
        log.warning("internal file request for an unknown reference")
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        handle = default_storage.open(version.file.name, "rb")
    except (FileNotFoundError, SuspiciousFileOperation):
        log.error(
            "a stored version's file is missing",
            extra={"document_version_id": str(version.id)},
        )
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    # Streamed, not read into memory: this process should not hold a 25 MB PDF
    # resident to hand it to a worker.
    return FileResponse(handle, content_type="application/pdf")
