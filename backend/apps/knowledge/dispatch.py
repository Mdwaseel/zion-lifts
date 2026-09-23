"""The boundary between Django and the ingestion worker.

Django never imports the worker. It knows two things about it — a task name and
an argument shape — and posts them to Redis; the worker lives in the
``ai_service`` image, where torch and the Qdrant client already are, and Django
stays a web application rather than acquiring a two-gigabyte ML dependency to
enqueue a job.

That means this module is the *entire* coupling between the two services, which
is why the task names are constants in one place and the payload is built by one
function. Anything else that wants to trigger ingestion goes through here.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from django.conf import settings

from zion.observability.context import get_request_id

log = logging.getLogger(__name__)

# Stable names, matched by the worker's own registration. Renaming one is a
# coordinated deployment: messages already in the queue carry the old name.
TASK_INGEST = "ai_service.ingest_document"
TASK_REINDEX = "ai_service.reindex_document"
TASK_DELETE = "ai_service.delete_document"

# The queue the ai_service workers consume. Named rather than default so the
# two services' tasks cannot end up interleaved on one queue.
QUEUE = "ai_ingestion"


class BrokerUnavailable(RuntimeError):
    """No broker is configured, so the job cannot be handed over.

    Raised rather than swallowed: a job row that says "queued" when nothing was
    queued is worse than an upload that fails loudly, because only one of those
    gets noticed.
    """


@lru_cache(maxsize=1)
def _app():
    """The Celery client, built once, lazily.

    Lazy because importing Django must not require a broker to exist — the test
    suite, `manage.py check` and every management command would otherwise need
    Redis running to do anything at all.
    """
    from celery import Celery

    broker = getattr(settings, "CELERY_BROKER_URL", "") or ""
    if not broker:
        raise BrokerUnavailable(
            "CELERY_BROKER_URL is not set (it defaults to REDIS_URL). "
            "Document ingestion needs a broker to hand work to ai_service."
        )

    app = Celery("zion-backend", broker=broker)
    app.conf.update(
        task_default_queue=QUEUE,
        # Django only ever sends. Telling Celery not to expect results keeps it
        # from reaching for a result backend that is not configured.
        task_ignore_result=True,
        broker_connection_retry_on_startup=True,
        # Fail fast on send: an upload request should not sit for 30 seconds
        # because Redis is unreachable.
        broker_transport_options={"max_retries": 2},
    )
    return app


def build_payload(version, *, job_id: str, operation: str = "ingest") -> dict[str, Any]:
    """The message body for one document version.

    Identifiers and a hash — never file bytes and never business data. The
    worker resolves ``file_reference`` against the storage it is configured
    with; the broker carries no document.

    ``job_id`` travels with it because the worker's reports come back naming a
    job, and the backend checks that the job, the document and the version
    genuinely describe each other before it writes anything.

    Mirrors ``IngestionRequest`` in ai_service/app/api/schemas/document.py. The
    two are a shared contract that no import enforces, so they change together.
    """
    document = version.document
    return {
        # The id that started this upload, carried into the worker so the whole
        # path — browser, Django, queue, ai_service — shares one correlation id.
        # A job triggered by a management command has none; the worker falls
        # back to the job id, which is still one id per attempt.
        "request_id": get_request_id(),
        "job_id": str(job_id),
        "document_id": str(document.id),
        "document_version_id": str(version.id),
        "knowledge_base_id": str(document.knowledge_base_id),
        "file_reference": version.file.name,
        "content_hash": version.content_hash,
        "embedding_model": version.embedding_model,
        "embedding_model_version": version.embedding_model_version,
        "operation": str(operation),
    }


def send(task_name: str, payload: dict[str, Any], *, task_id: str | None = None) -> str:
    """Hand one message to the broker and return its task id.

    ``task_id`` is supplied by the caller so that the id is decided before the
    send rather than after it: a job row is written with the id it expects, and
    a redelivery of the same message carries the same id rather than looking
    like new work.
    """
    result = _app().send_task(
        task_name,
        kwargs=payload,
        queue=QUEUE,
        task_id=task_id,
    )
    log.info(
        "ingestion_queued",
        extra={
            "event": "ingestion_queued",
            "task_name": task_name,
            "task_id": result.id,
            "queue": QUEUE,
            "job_id": payload.get("job_id"),
            "document_id": payload.get("document_id"),
            "document_version_id": payload.get("document_version_id"),
            "knowledge_base_id": payload.get("knowledge_base_id"),
            "operation": payload.get("operation"),
        },
    )
    return result.id
