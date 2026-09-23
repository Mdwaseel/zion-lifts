"""Operational health for the control room: ingestion, jobs, dependencies.

Three endpoints, staff-only through the same gate as the rest of the panel.
They answer "is the pipeline healthy", "what is stuck", and "are the providers
behaving" — the three questions somebody actually opens a dashboard to ask.

Two rules shape everything here.

*Read, never write.* Nothing on these endpoints retries a job, clears a
collection or changes a version. An operator looks and then decides; a dashboard
that repairs things on its own eventually repairs something that was not broken,
at the worst possible moment.

*Cheap enough to refresh.* Each endpoint is a small number of aggregate queries
and no fan-out. These get hit hardest exactly when the system is unwell, and a
diagnostic that adds load during an incident is part of the incident.
"""

from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.knowledge.models import IngestionJob
from apps.knowledge.selectors import operations as ops

from ..permissions import IsAdminPanelUser

# How many rows each list returns. Bounded so a backlog of ten thousand stale
# jobs produces a page, not a stall.
ROW_LIMIT = 25

# The dependency probe is a health check, not a request the user waits on.
PROBE_TIMEOUT = 2.0


class OperationsOverviewView(APIView):
    """The one-screen answer: is anything wrong right now?"""

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        snapshot = ops.ingestion_snapshot()
        stale_seconds = ops.stale_after_seconds()

        # "healthy" is deliberately conservative: anything stuck or failing
        # recently is worth a human's attention, and a dashboard that says
        # healthy while a document is wedged is a dashboard nobody trusts.
        if snapshot.stale:
            status = "degraded"
        elif snapshot.failed_24h:
            status = "attention"
        else:
            status = "healthy"

        return Response(
            {
                "status": status,
                "ingestion": snapshot.as_dict(),
                "thresholds": {"stale_after_seconds": stale_seconds},
                # Named windows rather than "today", which means different spans
                # to a reader in a different timezone than to the server.
                "windows": {"recent": "last_24_hours"},
            }
        )


class OperationsIngestionView(APIView):
    """What is stuck, what failed, and what keeps failing."""

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        return Response(
            {
                "stale_after_seconds": ops.stale_after_seconds(),
                "stale": [_job_row(job, stale=True) for job in ops.stale_jobs()[:ROW_LIMIT]],
                "recent_failures": [
                    _job_row(job) for job in ops.recent_failures()[:ROW_LIMIT]
                ],
                "repeatedly_failing": [
                    {
                        "document_id": str(document.id),
                        "name": document.name,
                        "knowledge_base": document.knowledge_base.name,
                        "recent_failures": document.recent_failures,
                    }
                    for document in ops.repeatedly_failing()[:ROW_LIMIT]
                ],
                "knowledge_bases": ops.knowledge_base_health(),
            }
        )


class OperationsProvidersView(APIView):
    """Dependency health, asked of ai_service rather than guessed at.

    Django does not hold the embedding or LLM state — the other service does —
    so this proxies its ops endpoint rather than keeping a second, staler copy.
    A failure to reach it is reported as an unreachable dependency, which is
    itself the answer an operator needs.
    """

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        base = (getattr(settings, "AI_SERVICE_URL", "") or "").rstrip("/")
        token = getattr(settings, "AI_SERVICE_OPS_TOKEN", "") or ""

        if not base or not token:
            return Response(
                {
                    "status": "unconfigured",
                    # Names the setting, never its value.
                    "detail": "AI_SERVICE_URL and AI_SERVICE_OPS_TOKEN are required "
                    "to read provider health.",
                }
            )

        try:
            response = httpx.get(
                f"{base}/api/v1/ops/providers",
                headers={"X-Internal-Token": token},
                timeout=PROBE_TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            # The exception type, not its message: an httpx error can carry the
            # full URL, and the URL carries the internal hostname.
            return Response(
                {"status": "unreachable", "error_type": type(exc).__name__}
            )

        return Response({"status": "ok", **response.json()})


def _job_row(job: IngestionJob, *, stale: bool = False) -> dict[str, Any]:
    """One job, as an operator needs to see it.

    Identifiers, status and timings. Never the error's stack trace, and the
    error message truncated — it is a summary line in a table, and an untrimmed
    provider error can be kilobytes of HTML.
    """
    row = {
        "job_id": str(job.id),
        "document_id": str(job.document_id),
        "document_version_id": str(job.document_version_id or ""),
        "document": job.document.name,
        "job_type": job.job_type,
        "status": job.status,
        "last_stage": job.current_stage,
        "progress": job.progress,
        "attempt_count": job.attempt_count,
        "error_code": job.error_code,
        "last_error": (job.error_message or "")[:200],
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "duration_seconds": job.duration_seconds,
    }
    if stale:
        row["stuck_for_seconds"] = _seconds_since(job.updated_at)
    return row


def _seconds_since(moment) -> int | None:
    from django.utils import timezone

    if moment is None:
        return None
    return int((timezone.now() - moment).total_seconds())
