"""Queuing work, and recording what the worker reports back.

A job row is written *before* the message is sent and the send happens after the
surrounding transaction commits. That order matters: a message that reaches a
worker before the row it refers to is visible is a message about a document that
does not exist yet, and Celery is quite fast enough for that to happen.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from django.db import transaction

from .. import dispatch
from ..models import Document, DocumentVersion, IngestionJob, JobStatus, JobType
from ..states import DocumentState, can_transition

log = logging.getLogger(__name__)

_TASK_FOR = {
    JobType.INGEST: dispatch.TASK_INGEST,
    JobType.REINDEX: dispatch.TASK_REINDEX,
    JobType.DELETE: dispatch.TASK_DELETE,
}


def active_job_for(version: DocumentVersion) -> IngestionJob | None:
    """A job for this version that has not finished, if there is one."""
    return version.jobs.filter(status__in=(JobStatus.QUEUED, JobStatus.RUNNING)).first()


@transaction.atomic
def queue(
    version: DocumentVersion,
    *,
    job_type: str = JobType.INGEST,
    force: bool = False,
) -> IngestionJob:
    """Create a job for ``version`` and hand it to the worker.

    Idempotent by default: asking twice while the first attempt is still in
    flight returns that attempt rather than starting a second worker on the same
    version, which would race to write the same chunk ids into the same
    collection. ``force`` is for a genuinely stuck job an operator is retrying.
    """
    if not force:
        existing = active_job_for(version)
        if existing is not None:
            log.info(
                "reusing in-flight job",
                extra={"job_id": str(existing.id), "document_version_id": str(version.id)},
            )
            return existing

    document = version.document

    # The task id is chosen here so the row and the message agree, and so a
    # redelivery is recognisable as the same work rather than as new work.
    task_id = str(uuid.uuid4())
    job = IngestionJob.objects.create(
        document=document,
        document_version=version,
        job_type=job_type,
        status=JobStatus.QUEUED,
        celery_task_id=task_id,
        attempt_count=version.jobs.count() + 1,
    )

    if version.status != DocumentState.PROCESSING:
        version.transition_to(DocumentState.PROCESSING)

    # Only a document with nothing live follows its version into PROCESSING.
    # One that is already serving stays READY for as long as it keeps
    # answering: the new edition is in flight, but the document is not down,
    # and showing it as PROCESSING would say the corpus had a gap it does not
    # have. The job's own progress is where the in-flight work is visible.
    if document.active_version_id is None and document.status != DocumentState.PROCESSING:
        document.transition_to(DocumentState.PROCESSING)

    payload = dispatch.build_payload(version, job_id=str(job.id), operation=job_type)
    task_name = _TASK_FOR[job_type]

    # After commit, so the worker cannot arrive before the rows it describes.
    transaction.on_commit(lambda: _send(job, task_name, payload, task_id))
    return job


def _send(job: IngestionJob, task_name: str, payload: dict, task_id: str) -> None:
    try:
        dispatch.send(task_name, payload, task_id=task_id)
    except Exception as exc:  # broker down, misconfigured, unreachable
        # The upload itself succeeded and the file is stored; only the handover
        # failed. Say so on the job so it shows as retryable in the control
        # room rather than sitting at "queued" forever.
        log.exception("could not queue %s", task_name, extra={"job_id": str(job.id)})
        job.mark_failed("broker_unavailable", str(exc))

        # Through the service, not a queryset update. A bulk `update()` writes
        # the version's status and nothing else, which left the *document* at
        # PROCESSING for ever: the control room showed "Queued", and Retry is
        # only offered for a failed document, so a broker outage produced a
        # document that could never be recovered from the panel.
        version = DocumentVersion.objects.filter(pk=job.document_version_id).first()
        if version is not None:
            from . import version_service

            version_service.fail_version(
                version, code="broker_unavailable", message=str(exc)
            )


def report_stage(job: IngestionJob, stage: str, *, task_id: str = "") -> IngestionJob:
    """Record progress reported by the worker, moving the version with it."""
    job.mark_running(stage, task_id=task_id)

    version = job.document_version
    if version is not None and version.status != stage:
        version.transition_to(stage)
        document = version.document
        if document.status != stage and document.active_version_id is None:
            # A document with nothing live follows its only version's stage, so
            # the control room shows real progress on a first upload. One that
            # is already serving stays READY until the new edition replaces it.
            document.transition_to(stage)
    return job


# --- the worker callback ----------------------------------------------------


@dataclass(slots=True)
class ReportOutcome:
    """What became of one report. Returned rather than logged so the endpoint
    can say plainly whether anything changed."""

    applied: bool
    action: str


def locate_job(*, job_id, document_id, document_version_id) -> IngestionJob | None:
    """Find the job a report claims to be about, or None.

    All three identifiers must agree with what is stored. Looking the job up by
    id alone and believing the rest would let a caller holding one valid job id
    write counts and statuses onto any document in the system — the ids travel
    together, so they are checked together.
    """
    return (
        IngestionJob.objects.select_related("document", "document_version")
        .filter(
            pk=job_id,
            document_id=document_id,
            document_version_id=document_version_id,
        )
        .first()
    )


@transaction.atomic
def apply_report(job: IngestionJob, report: dict) -> ReportOutcome:
    """Apply one worker report to the job, its version and its document.

    Written to be safe against the two things that actually happen in a queue:
    the same message arriving twice, and an old message arriving after a newer
    one. Both are ignored rather than treated as errors — the worker is not
    misbehaving, the network is.
    """
    stage = report["stage"]

    # A job that has already reached a conclusion is finished. A straggler from
    # a superseded attempt must not reopen it and drag a live document back into
    # PROCESSING.
    if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED):
        if stage == job.current_stage:
            return ReportOutcome(applied=False, action="duplicate")
        return ReportOutcome(applied=False, action="stale_job_finished")

    version = job.document_version
    if version is None:
        return ReportOutcome(applied=False, action="no_version")

    # The same stage twice is the common case — a retried callback, or a worker
    # repeating itself. Counts may have improved, so they are refreshed, but no
    # transition is attempted.
    if stage == job.current_stage and stage not in (DocumentState.READY, DocumentState.FAILED):
        _absorb_counts(version, report)
        return ReportOutcome(applied=True, action="progress_refreshed")

    if stage == DocumentState.FAILED:
        return _apply_failure(job, version, report)
    if stage == DocumentState.READY:
        return _apply_ready(job, version, report)
    if stage in (DocumentState.DELETING, DocumentState.DELETED):
        return _apply_deletion(job, version, stage)

    return _apply_progress(job, version, stage, report)


def _absorb_counts(version: DocumentVersion, report: dict) -> None:
    """Store whatever the worker has measured so far.

    Only ever the values it observed while processing; nothing here is taken
    from the original request, so a count always describes the run that
    produced it.
    """
    fields: list[str] = []
    for name in ("page_count", "chunk_count", "embedding_dimension"):
        value = report.get(name)
        if value is not None and getattr(version, name) != value:
            setattr(version, name, value)
            fields.append(name)

    for name in ("embedding_model", "embedding_model_version", "collection"):
        value = report.get(name)
        if value and getattr(version, name) != value:
            setattr(version, name, value)
            fields.append(name)

    if fields:
        version.save(update_fields=[*fields, "updated_at"])


def _apply_progress(
    job: IngestionJob, version: DocumentVersion, stage: str, report: dict
) -> ReportOutcome:
    if not can_transition(version.status, stage):
        # Out of order. Between an in-flight stage and one the lifecycle does
        # not allow from here, the stored state is the one to keep: it came
        # from a message we already accepted.
        return ReportOutcome(applied=False, action="out_of_order")

    _absorb_counts(version, report)
    report_stage(job, stage, task_id=report.get("task_id", ""))
    return ReportOutcome(applied=True, action="advanced")


def _apply_ready(job: IngestionJob, version: DocumentVersion, report: dict) -> ReportOutcome:
    """Finish a successful run, and only now make the version live.

    This is the single place a version becomes active, and it happens after the
    worker has said the whole index is written — which is what keeps the
    previous edition answering right up until its replacement can.
    """
    from . import version_service

    if version.status == DocumentState.READY and version.is_active:
        return ReportOutcome(applied=False, action="duplicate")

    if not can_transition(version.status, DocumentState.READY):
        return ReportOutcome(applied=False, action="out_of_order")

    version_service.complete_version(
        version,
        page_count=report.get("page_count"),
        chunk_count=report.get("chunk_count"),
        embedding_dimension=report.get("embedding_dimension"),
        collection=report.get("collection") or "",
        embedding_model=report.get("embedding_model") or "",
        embedding_model_version=report.get("embedding_model_version") or "",
    )
    job.mark_succeeded()
    return ReportOutcome(applied=True, action="activated")


def _apply_failure(job: IngestionJob, version: DocumentVersion, report: dict) -> ReportOutcome:
    from . import version_service

    if version.status == DocumentState.FAILED:
        return ReportOutcome(applied=False, action="duplicate")

    version_service.fail_version(
        version,
        code=report.get("error_code") or "ingestion_failed",
        message=report.get("error_message") or "",
    )
    job.mark_failed(
        report.get("error_code") or "ingestion_failed",
        report.get("error_message") or "",
    )
    return ReportOutcome(applied=True, action="failed")


def _apply_deletion(job: IngestionJob, version: DocumentVersion, stage: str) -> ReportOutcome:
    """Advance a delete job. The document row survives its own deletion here:
    what has gone is its vectors, and the record of that is worth keeping."""
    document = version.document

    if stage == DocumentState.DELETING:
        if document.status == DocumentState.DELETING:
            return ReportOutcome(applied=False, action="duplicate")
        if not can_transition(document.status, DocumentState.DELETING):
            return ReportOutcome(applied=False, action="out_of_order")
        document.transition_to(DocumentState.DELETING)
        job.mark_running(DocumentState.DELETING)
        return ReportOutcome(applied=True, action="advanced")

    if document.status == DocumentState.DELETED:
        return ReportOutcome(applied=False, action="duplicate")
    if not can_transition(document.status, DocumentState.DELETED):
        return ReportOutcome(applied=False, action="out_of_order")

    document.transition_to(DocumentState.DELETED)
    job.mark_succeeded()
    return ReportOutcome(applied=True, action="deleted")


def documents_needing_attention() -> int:
    """How many documents an operator should look at. Used by the dashboard."""
    return Document.objects.filter(status=DocumentState.FAILED).count()
