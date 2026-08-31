"""The operations the generic admin CRUD cannot express.

Everything here is staff-only, through the same gate the rest of the control
room uses. The views are thin by design — they parse, delegate to
``services``, and translate a domain exception into a status code. No lifecycle
decision is made in this module.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Prefetch
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.adminpanel.permissions import IsAdminPanelUser

from ..models import Document, IngestionJob
from ..selectors import documents as document_selectors
from ..selectors import knowledge_bases as kb_selectors
from ..services import document_service
from ..states import InvalidTransition
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentVersionSerializer,
    IngestionJobSerializer,
    KnowledgeBaseSerializer,
    VersionUploadSerializer,
)


def _problem(exc: Exception, code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    """One shape for every refusal, matching what DRF returns elsewhere."""
    detail = getattr(exc, "messages", None) or [str(exc)]
    return Response({"detail": " ".join(detail)}, status=code)


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    """Corpora. Ordinary CRUD — a knowledge base is just a name and a switch."""

    serializer_class = KnowledgeBaseSerializer
    permission_classes = [IsAdminPanelUser]

    def get_queryset(self):
        return kb_selectors.with_counts().order_by("name")


class DocumentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Documents, plus the actions that move them through their lifecycle.

    No ``create`` and no ``destroy``: a document is created by uploading a file
    (``POST upload/``) and removed by a job that clears its vectors first
    (``POST {id}/delete/``). Both are operations, not row writes, and giving
    them their own names keeps the difference visible.
    """

    serializer_class = DocumentSerializer
    permission_classes = [IsAdminPanelUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        # `recent_jobs` feeds the progress shown on each row; without the
        # prefetch a fifty-document list is fifty-one queries.
        recent = Prefetch(
            "jobs",
            queryset=IngestionJob.objects.order_by("-created_at")[:1],
            to_attr="recent_jobs",
        )
        queryset = (
            document_selectors.documents(
                self.request.query_params.get("knowledge_base") or None
            )
            .annotate(version_count=Count("versions", distinct=True))
            .prefetch_related(recent)
        )
        state = self.request.query_params.get("status")
        if state:
            queryset = queryset.filter(status=state)
        # Explicit, not inherited: annotate() drops the Meta ordering, and an
        # unordered queryset paginates inconsistently — page 2 can repeat a row
        # from page 1.
        return queryset.order_by("-created_at")

    @action(detail=False, methods=["post"])
    def upload(self, request):
        """Accept a PDF as a new document and queue its first ingestion."""
        form = DocumentUploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        try:
            document, version, job = document_service.create_document(
                knowledge_base=form.validated_data["knowledge_base"],
                upload=form.validated_data["file"],
                name=form.validated_data.get("name", ""),
                created_by=request.user,
            )
        except DjangoValidationError as exc:
            return _problem(exc)

        return Response(
            {
                "document": DocumentSerializer(document).data,
                "version": DocumentVersionSerializer(version).data,
                "job": IngestionJobSerializer(job).data if job else None,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def versions(self, request, pk=None):
        """GET lists the editions of this document; POST stores a new one.

        One action rather than two, because two actions with the same
        ``url_path`` silently register the same route twice and the second is
        never reached — the GET arrives at the POST-only handler and comes back
        405.
        """
        if request.method == "GET":
            document = self.get_object()
            return Response(
                DocumentVersionSerializer(
                    document_selectors.versions(document), many=True
                ).data
            )
        return self._add_version(request)

    def _add_version(self, request):
        """Store a replacement edition. The live one keeps serving until the
        new one is indexed."""
        document = self.get_object()
        form = VersionUploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        try:
            version, job = document_service.add_version(
                document,
                upload=form.validated_data["file"],
                allow_duplicate=form.validated_data["allow_duplicate"],
            )
        except document_service.DuplicateContent as exc:
            return Response(
                {
                    "detail": " ".join(exc.messages),
                    "code": "duplicate_content",
                    "version": DocumentVersionSerializer(exc.version).data,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except DjangoValidationError as exc:
            return _problem(exc)

        return Response(
            {
                "version": DocumentVersionSerializer(version).data,
                "job": IngestionJobSerializer(job).data if job else None,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def jobs(self, request, pk=None):
        document = self.get_object()
        return Response(
            IngestionJobSerializer(document_selectors.jobs(document)[:20], many=True).data
        )

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Just enough to poll while something is processing."""
        document = self.get_object()
        job = document_selectors.latest_job(document)
        return Response(
            {
                "document_id": str(document.id),
                "status": document.status,
                "active_version": (
                    document.active_version.version_number if document.active_version else None
                ),
                "job": IngestionJobSerializer(job).data if job else None,
            }
        )

    @action(detail=True, methods=["post"])
    def reindex(self, request, pk=None):
        document = self.get_object()
        try:
            job = document_service.reindex(document)
        except (DjangoValidationError, InvalidTransition) as exc:
            return _problem(exc, status.HTTP_409_CONFLICT)
        return Response(IngestionJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        document = self.get_object()
        try:
            job = document_service.retry(document)
        except (DjangoValidationError, InvalidTransition) as exc:
            return _problem(exc, status.HTTP_409_CONFLICT)
        return Response(IngestionJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="delete")
    def request_delete(self, request, pk=None):
        """Begin removal. The record survives until its vectors are gone."""
        document = self.get_object()
        try:
            job = document_service.request_deletion(document)
        except (DjangoValidationError, InvalidTransition) as exc:
            return _problem(exc, status.HTTP_409_CONFLICT)
        return Response(IngestionJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class IngestionJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only history of what the workers have been asked to do."""

    serializer_class = IngestionJobSerializer
    permission_classes = [IsAdminPanelUser]

    def get_queryset(self):
        queryset = document_selectors.jobs()
        state = self.request.query_params.get("status")
        document = self.request.query_params.get("document")
        if state:
            queryset = queryset.filter(status=state)
        if document:
            queryset = queryset.filter(document_id=document)
        return queryset
