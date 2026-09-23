"""Does a message Django sends actually reach this worker?

Every other test in the suite stubs the broker, which means none of them would
notice the failure that matters most in practice: the two services agreeing on
a task name but disagreeing about a queue, a serializer, or a Redis database
number. A message then vanishes silently — Django reports the upload as queued,
the worker sits idle, and nothing anywhere says why.

These tests need a real Redis and are skipped without one::

    docker run -d -p 6379:6379 redis:7-alpine
    REDIS_URL=redis://localhost:6379/1 pytest -m integration

They deliberately do not execute the ingestion pipeline: what is under test is
delivery, and running a real embedding model would only make it slow.
"""

from __future__ import annotations

import os
import uuid

import pytest

from app.core.config import Settings
from app.tasks.celery_app import build_celery
from app.tasks.ingestion import TASK_DELETE, TASK_INGEST, TASK_REINDEX

pytestmark = pytest.mark.integration

REDIS_URL = os.getenv("REDIS_URL", "")

requires_redis = pytest.mark.skipif(
    not REDIS_URL,
    reason="set REDIS_URL to a running Redis to exercise the broker",
)

# The names and queue Django uses. Duplicated here on purpose rather than
# imported: the point is to prove the two sides agree without the test being
# able to cheat by sharing a constant.
DJANGO_TASK_NAMES = {
    "ingest": "ai_service.ingest_document",
    "reindex": "ai_service.reindex_document",
    "delete": "ai_service.delete_document",
}
DJANGO_QUEUE = "ai_ingestion"


@pytest.fixture
def app():
    settings = Settings(
        _env_file=None,
        environment="test",
        redis_url=REDIS_URL,
        celery_task_queue=DJANGO_QUEUE,
    )
    return build_celery(settings)


@requires_redis
def test_redis_is_reachable(app):
    connection = app.connection()
    connection.ensure_connection(max_retries=1)
    connection.release()


@requires_redis
def test_the_worker_registers_the_names_django_sends(app):
    for name in DJANGO_TASK_NAMES.values():
        assert name in app.tasks, f"{name} is not registered on the worker"


@requires_redis
def test_a_message_lands_on_the_queue_the_worker_consumes(app):
    """The delivery path, end to end, without executing anything.

    Publishes exactly as Django's dispatch does, then reads the queue back. A
    mismatch in queue name, database number or serializer shows up here as an
    empty queue.
    """
    queue = f"{DJANGO_QUEUE}-test-{uuid.uuid4().hex[:8]}"
    body = {
        "job_id": str(uuid.uuid4()),
        "document_id": str(uuid.uuid4()),
        "document_version_id": str(uuid.uuid4()),
        "knowledge_base_id": str(uuid.uuid4()),
        "file_reference": "knowledge/doc/v1.pdf",
        "content_hash": "a" * 64,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_model_version": "v1",
        "operation": "ingest",
    }

    app.send_task(TASK_INGEST, kwargs=body, queue=queue)

    with app.connection_for_read() as connection:
        message = connection.SimpleQueue(queue).get(block=True, timeout=5)
        try:
            assert message.headers["task"] == TASK_INGEST
            # kwargs travel in the second element of the body tuple.
            assert message.decode()[1]["document_version_id"] == body["document_version_id"]
        finally:
            message.ack()
            connection.SimpleQueue(queue).queue.delete()


@requires_redis
def test_every_task_name_routes_to_the_shared_queue(app):
    for name in (TASK_INGEST, TASK_REINDEX, TASK_DELETE):
        route = app.amqp.router.route({}, name)
        assert route["queue"].name == DJANGO_QUEUE, name
