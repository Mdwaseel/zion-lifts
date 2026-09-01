"""The three tasks Django enqueues.

Each one is a wrapper: validate the message, hand it to the pipeline, decide
whether a failure is worth another attempt. The workflow lives in
``app.ingestion.pipeline`` — a task body is the wrong place for it, because
everything in here runs under Celery and nothing in here can be tested without
it.

The retry policy is the substance of these functions:

* a **permanent** failure — a corrupt PDF, a hash that does not match, vectors
  of the wrong width — is reported to the backend and the message is finished.
  Retrying it produces the same failure three more times and delays every other
  document in the queue behind it.
* a **transient** failure — Qdrant unreachable, a provider rate-limiting, the
  callback timing out — is retried with exponential backoff, and the backend is
  told only when the attempts run out. A job that is about to be tried again is
  still running, and saying otherwise would have an operator chasing a document
  that was going to fix itself.
"""

from __future__ import annotations

import random
import time
from typing import Any

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import worker_process_shutdown
from pydantic import ValidationError

from app.api.schemas.document import IngestionRequest
from app.core import events
from app.core.errors import IngestionError, InvalidPayload, classify
from app.core.logging import get_logger, set_request_id
from app.core.metrics import metrics
from app.tasks import runtime

logger = get_logger(__name__)

TASK_INGEST = "ai_service.ingest_document"
TASK_REINDEX = "ai_service.reindex_document"
TASK_DELETE = "ai_service.delete_document"


def _parse(payload: dict[str, Any]) -> IngestionRequest:
    try:
        return IngestionRequest.model_validate(payload)
    except ValidationError as exc:
        # Permanent by construction: the same malformed message will not become
        # valid on a second delivery.
        raise InvalidPayload(f"the ingestion message is not valid: {exc}") from exc


def _run(task: Any, payload: dict[str, Any], operation: str) -> dict[str, Any]:
    """Shared body: parse, dispatch, classify, report, retry or give up."""
    request = _parse(payload)

    # The correlation id Django sent, so one upload can be followed from the
    # HTTP request through the queue and into this worker. A task triggered by
    # hand carries none, and the job id stands in — still one id per attempt,
    # just one that starts here rather than at a browser.
    correlation_id = str(payload.get("request_id") or "").strip()
    set_request_id(correlation_id[:64] if correlation_id else request.job_id[:16])

    context = runtime.context()
    attempt = (task.request.retries or 0) + 1
    base = {
        "task_id": task.request.id,
        "job_id": request.job_id,
        "document_id": request.document_id,
        "document_version_id": request.document_version_id,
        "knowledge_base_id": request.knowledge_base_id,
        "operation": operation,
        "attempt": attempt,
    }

    metrics.increment("celery_tasks_total", task=operation)
    logger.info(events.CELERY_TASK_STARTED, extra={"event": events.CELERY_TASK_STARTED, **base})
    started = time.perf_counter()

    try:
        if operation == "delete":
            removed = runtime.run(context.pipeline.delete(request))
            _record_success(operation, started, base)
            return {"removed": removed, **base}

        outcome = runtime.run(context.pipeline.ingest(request))
        _record_success(operation, started, base)
        return {
            "chunks": outcome.chunk_count,
            "pages": outcome.page_count,
            "collection": outcome.collection,
            "duration_ms": round(outcome.took_ms, 1),
            **base,
        }

    except SoftTimeLimitExceeded as exc:
        # The child is about to be killed. Report before that happens, or the
        # job sits at RUNNING for ever with nothing to explain it.
        error = classify(exc)
        error.retryable = True
        return _handle_failure(task, context, request, error, base)

    except Exception as exc:
        return _handle_failure(task, context, request, classify(exc), base)


def _record_success(operation: str, started: float, base: dict[str, Any]) -> None:
    took = (time.perf_counter() - started) * 1000
    metrics.increment("celery_task_success_total", task=operation)
    metrics.observe("celery_task_duration", took, task=operation, status="ok")
    logger.info(
        events.CELERY_TASK_COMPLETED,
        extra={"event": events.CELERY_TASK_COMPLETED, **base, "duration_ms": round(took, 1)},
    )


def _handle_failure(
    task: Any,
    context: runtime.WorkerContext,
    request: IngestionRequest,
    error: IngestionError,
    base: dict[str, Any],
) -> dict[str, Any]:
    max_retries = context.settings.celery_task_max_retries
    attempts_left = error.retryable and (task.request.retries or 0) < max_retries

    logger.exception("Ingestion failed with error: %s", error)
    logger.warning(
        events.INGESTION_RETRYING if attempts_left else events.INGESTION_FAILED,
        extra={
            "event": events.INGESTION_RETRYING if attempts_left else events.INGESTION_FAILED,
            **base,
            "error_code": str(error.code),
            "exception_type": type(error).__name__,
            "retryable": error.retryable,
            "will_retry": attempts_left,
            "max_attempts": max_retries + 1,
        },
    )

    if attempts_left:
        # Exponential, capped, and jittered. The jitter is the part that
        # matters: without it every document queued behind a Qdrant restart
        # comes back at the same instant, and the retry storm is what keeps the
        # dependency down. Full jitter over [0, delay] rather than a small
        # wobble, because the goal is to spread the herd, not to nudge it.
        ceiling = min(
            context.settings.celery_retry_backoff * (2 ** (task.request.retries or 0)),
            context.settings.celery_retry_backoff_max,
        )
        delay = round(random.uniform(0, ceiling), 1)
        metrics.increment("celery_task_retry_total", task=base.get("operation", "unknown"))
        metrics.increment("ingestion_jobs_retried_total")
        logger.info(
            events.CELERY_TASK_RETRYING,
            extra={
                "event": events.CELERY_TASK_RETRYING,
                **base,
                "error_code": str(error.code),
                "max_attempts": max_retries + 1,
                "retry_in_s": delay,
                "backoff_ceiling_s": ceiling,
            },
        )
        raise task.retry(exc=error, countdown=delay)

    # Out of attempts, or never worth retrying. Tell the backend, and let the
    # task finish — a raised exception here would only be a second record of a
    # failure that is already recorded where an operator will look for it.
    try:
        runtime.run(context.pipeline.report_failure(request, error))
    except Exception as report_error:
        # Nothing else to try. The job stays RUNNING and the reconciliation in
        # Phase 4 is what will find it; losing the log line as well would make
        # it invisible.
        logger.error(
            "could not report failure to the backend",
            extra={**base, "error_code": str(error.code), "err": str(report_error)},
        )

    metrics.increment("celery_task_failure_total", task=base.get("operation", "unknown"))
    metrics.increment("ingestion_jobs_failed_total", error_code=str(error.code))
    logger.error(
        events.CELERY_TASK_FAILED,
        extra={
            "event": events.CELERY_TASK_FAILED,
            **base,
            "error_code": str(error.code),
            "exception_type": type(error).__name__,
        },
    )
    return {"failed": True, "error_code": str(error.code), **base}


@shared_task(bind=True, name=TASK_INGEST, max_retries=None, acks_late=True)
def ingest_document(self: Any, **payload: Any) -> dict[str, Any]:
    """Index a document version for the first time."""
    return _run(self, payload, "ingest")


@shared_task(bind=True, name=TASK_REINDEX, max_retries=None, acks_late=True)
def reindex_document(self: Any, **payload: Any) -> dict[str, Any]:
    """Rebuild a version's vectors in place, keeping its identity."""
    return _run(self, payload, "reindex")


@shared_task(bind=True, name=TASK_DELETE, max_retries=None, acks_late=True)
def delete_document(self: Any, **payload: Any) -> dict[str, Any]:
    """Remove a document's chunks from the index."""
    return _run(self, payload, "delete")


@worker_process_shutdown.connect
def _close_runtime(**_: Any) -> None:
    """Release this child's clients when Celery stops it."""
    runtime.shutdown()
