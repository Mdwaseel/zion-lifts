"""Operational read queries: what is running, what broke, what is stuck.

Everything here is written to be one query. These feed a dashboard an operator
refreshes while something is going wrong, which is exactly when the database is
least able to absorb a page of N+1 lookups — a diagnostic that adds load during
an incident is part of the incident.

On *stale* jobs, which is the one idea in this module worth stating plainly:

A job is stale when it has been in flight longer than any real run should take.
That is a signal, not a verdict. A worker whose machine was restarted and a
worker chewing through a 900-page scan look identical from here — both are rows
that say RUNNING and have not been updated in a while — and only one of them is
safe to give up on. So nothing in this module writes. It reports, an operator
looks, and a human decides whether to retry. Automatically failing these would
eventually kill a healthy long run and leave its vectors half-written.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from ..models import Document, DocumentVersion, IngestionJob, JobStatus
from ..states import IN_FLIGHT, DocumentState

# Jobs that have not finished. Both, because a job that never left QUEUED is
# just as stuck as one that stopped halfway — and points at a different
# problem: no worker is consuming, rather than a worker that died mid-run.
UNFINISHED = (JobStatus.QUEUED, JobStatus.RUNNING)


def stale_after_seconds() -> int:
    return int(getattr(settings, "INGESTION_STALE_AFTER_SECONDS", 1800))


def stale_cutoff(seconds: int | None = None):
    """The timestamp before which an unfinished job counts as stale.

    Timezone-aware via ``timezone.now()`` rather than ``datetime.now()``: the
    comparison is against a stored aware datetime, and a naive one here would
    silently shift the threshold by the server's UTC offset.
    """
    return timezone.now() - timedelta(seconds=seconds or stale_after_seconds())


def unfinished_jobs() -> QuerySet[IngestionJob]:
    return IngestionJob.objects.filter(status__in=UNFINISHED)


def stale_jobs(seconds: int | None = None) -> QuerySet[IngestionJob]:
    """Unfinished jobs whose last sign of life is older than the threshold.

    Measured from ``updated_at``, not ``created_at``. The worker touches the row
    at every stage transition, so a job that is slowly but genuinely progressing
    keeps refreshing it — which is the difference between "this is taking a
    while" and "nothing has happened for half an hour".
    """
    return (
        unfinished_jobs()
        .filter(updated_at__lt=stale_cutoff(seconds))
        .select_related("document", "document_version")
        .order_by("updated_at")
    )


def recent_failures(hours: int = 24) -> QuerySet[IngestionJob]:
    since = timezone.now() - timedelta(hours=hours)
    return (
        IngestionJob.objects.filter(status=JobStatus.FAILED, updated_at__gte=since)
        .select_related("document", "document_version")
        .order_by("-updated_at")
    )


def repeatedly_failing(hours: int = 24, threshold: int = 2) -> QuerySet[Document]:
    """Documents that have failed more than once lately.

    The distinction an operator needs when triaging: one failure is usually a
    dependency having a bad minute, while the same document failing three times
    is a bad document, and re-running it will produce a fourth.
    """
    since = timezone.now() - timedelta(hours=hours)
    return (
        Document.objects.annotate(
            recent_failures=Count(
                "jobs",
                filter=Q(jobs__status=JobStatus.FAILED, jobs__updated_at__gte=since),
            )
        )
        .filter(recent_failures__gte=threshold)
        .select_related("knowledge_base")
        .order_by("-recent_failures")
    )


@dataclass(frozen=True)
class IngestionSnapshot:
    """Ingestion at a glance, from one aggregate query."""

    queued: int
    running: int
    stale: int
    succeeded_24h: int
    failed_24h: int
    retried_24h: int

    def as_dict(self) -> dict[str, int]:
        return {
            "queued": self.queued,
            "running": self.running,
            "stale": self.stale,
            "succeeded_24h": self.succeeded_24h,
            "failed_24h": self.failed_24h,
            "retried_24h": self.retried_24h,
        }


def ingestion_snapshot(stale_seconds: int | None = None) -> IngestionSnapshot:
    """Every ingestion count a dashboard needs, in a single round trip.

    Conditional aggregates rather than six ``.count()`` calls: the six would be
    six queries, and would also be six *different moments*, so a job finishing
    between them could be counted twice or not at all.
    """
    day_ago = timezone.now() - timedelta(hours=24)
    cutoff = stale_cutoff(stale_seconds)

    counts = IngestionJob.objects.aggregate(
        queued=Count("id", filter=Q(status=JobStatus.QUEUED)),
        running=Count("id", filter=Q(status=JobStatus.RUNNING)),
        stale=Count("id", filter=Q(status__in=UNFINISHED, updated_at__lt=cutoff)),
        succeeded_24h=Count(
            "id", filter=Q(status=JobStatus.SUCCEEDED, updated_at__gte=day_ago)
        ),
        failed_24h=Count("id", filter=Q(status=JobStatus.FAILED, updated_at__gte=day_ago)),
        # A job with more than one attempt was retried at least once. Counting
        # attempts rather than rows would need a sum, and the number an operator
        # wants is "how many runs needed a second go".
        retried_24h=Count(
            "id", filter=Q(attempt_count__gt=1, updated_at__gte=day_ago)
        ),
    )
    return IngestionSnapshot(**{k: int(v or 0) for k, v in counts.items()})


def knowledge_base_health(knowledge_base_id: Any = None) -> list[dict[str, Any]]:
    """Per-knowledge-base document counts and the last successful ingestion.

    One query with conditional aggregates, for the reason given at the top of
    this module. Chunk totals come from the versions rather than from Qdrant:
    asking the vector store would make a dashboard refresh depend on the health
    of the dependency it is meant to be reporting on.
    """
    from ..models import KnowledgeBase

    queryset = KnowledgeBase.objects.all()
    if knowledge_base_id is not None:
        queryset = queryset.filter(id=knowledge_base_id)

    rows = queryset.annotate(
        total_documents=Count("documents", distinct=True),
        ready_documents=Count(
            "documents", filter=Q(documents__status=DocumentState.READY), distinct=True
        ),
        processing_documents=Count(
            "documents", filter=Q(documents__status__in=IN_FLIGHT), distinct=True
        ),
        failed_documents=Count(
            "documents", filter=Q(documents__status=DocumentState.FAILED), distinct=True
        ),
    ).order_by("name")

    return [
        {
            "knowledge_base_id": str(row.id),
            "name": row.name,
            "is_active": row.is_active,
            "total_documents": row.total_documents,
            "ready_documents": row.ready_documents,
            "processing_documents": row.processing_documents,
            "failed_documents": row.failed_documents,
        }
        for row in rows
    ]


def version_health(document: Document) -> dict[str, Any]:
    """Active versus latest edition, and whether they disagree.

    The distinction that matters operationally: a document can be answering
    perfectly from version 2 while version 3 sits FAILED. Reporting only the
    document's own status would call that "ready" and hide a broken upload, and
    reporting only the newest version would call it "failed" and send somebody
    hunting for an outage that is not affecting anyone.
    """
    latest = (
        DocumentVersion.objects.filter(document=document)
        .order_by("-version_number")
        .first()
    )
    active = document.active_version

    return {
        "active_version": active.version_number if active else None,
        "latest_version": latest.version_number if latest else None,
        "latest_version_status": latest.status if latest else None,
        # True when the newest upload did not become the live one — the case
        # worth surfacing, because nothing else about the document looks wrong.
        "latest_version_is_not_active": bool(
            latest and active and latest.version_number != active.version_number
        ),
    }
