"""The Celery layer: registration, the contract with Django, and retry policy.

Deliberately not run through Celery's eager mode. Eager mode executes the
function body but skips the parts that actually matter here — routing, task
names, and what ``self.retry`` does — so a suite built on it can pass while the
worker consumes nothing. These call the task functions with a stub request and
assert on the decisions they make.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.api.schemas.document import IngestionRequest
from app.core.config import Settings
from app.core.errors import (
    DocumentNotFound,
    EmbeddingDimensionMismatch,
    InvalidPayload,
    VectorStoreUnavailable,
)
from app.tasks import ingestion, runtime
from app.tasks.celery_app import build_celery

BARE = {"_env_file": None}


def payload(**overrides: Any) -> dict[str, Any]:
    """A message shaped exactly as Django's dispatch.build_payload emits one."""
    body = {
        "job_id": "job-1",
        "document_id": "doc-1",
        "document_version_id": "ver-1",
        "knowledge_base_id": "kb-7",
        "file_reference": "knowledge/doc-1/v1.pdf",
        "content_hash": "a" * 64,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_model_version": "v1",
        "operation": "ingest",
    }
    body.update(overrides)
    return body


class Retried(Exception):
    """What the stub task raises in place of Celery's own retry."""

    def __init__(self, countdown: int) -> None:
        self.countdown = countdown


class StubTask:
    """Enough of a bound Celery task for the retry logic to be exercised."""

    def __init__(self, retries: int = 0) -> None:
        self.request = type("Req", (), {"retries": retries, "id": "task-1"})()

    def retry(self, exc: Exception, countdown: int) -> Exception:
        return Retried(countdown)


class StubPipeline:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.ingested: list[IngestionRequest] = []
        self.failures: list[Any] = []
        self.deleted: list[IngestionRequest] = []

    async def ingest(self, request):
        if self.error:
            raise self.error
        self.ingested.append(request)
        from app.ingestion.pipeline import IngestionOutcome

        return IngestionOutcome(
            document_version_id=request.document_version_id,
            collection="kb_kb_7__fake_v1",
            page_count=3,
            chunk_count=9,
            embedding_model="fake",
            embedding_dimension=8,
            took_ms=1.0,
        )

    async def delete(self, request):
        if self.error:
            raise self.error
        self.deleted.append(request)
        return 9

    async def report_failure(self, request, error):
        self.failures.append(error)


@pytest.fixture
def worker(monkeypatch):
    """Install a stub runtime so no model loads and no socket opens."""
    pipeline = StubPipeline()
    context = type("Ctx", (), {"settings": Settings(**BARE), "pipeline": pipeline})()
    monkeypatch.setattr(runtime, "context", lambda *a, **k: context)
    return pipeline


class TestRegistration:
    def test_the_three_tasks_are_registered_under_their_public_names(self):
        app = build_celery(Settings(**BARE, environment="test"))
        registered = {name for name in app.tasks if name.startswith("ai_service.")}
        assert registered == {
            "ai_service.ingest_document",
            "ai_service.reindex_document",
            "ai_service.delete_document",
        }

    def test_the_names_are_explicit_not_derived_from_the_module(self):
        # Django sends by name. Deriving them from a Python path would make an
        # innocuous refactor a silent production outage.
        assert ingestion.TASK_INGEST == "ai_service.ingest_document"
        assert ingestion.ingest_document.name == ingestion.TASK_INGEST
        assert ingestion.reindex_document.name == ingestion.TASK_REINDEX
        assert ingestion.delete_document.name == ingestion.TASK_DELETE

    def test_tasks_are_routed_to_the_shared_queue(self):
        app = build_celery(Settings(**BARE, environment="test"))
        assert app.conf.task_default_queue == "ai_ingestion"

    def test_only_json_is_accepted(self):
        # Pickle would let a message run arbitrary code in the worker.
        app = build_celery(Settings(**BARE, environment="test"))
        assert app.conf.task_serializer == "json"
        assert app.conf.accept_content == ["json"]

    def test_acknowledgement_is_late_so_a_lost_worker_loses_no_work(self):
        app = build_celery(Settings(**BARE, environment="test"))
        assert app.conf.task_acks_late is True
        assert app.conf.task_reject_on_worker_lost is True

    def test_concurrency_defaults_to_one(self):
        # Each child holds its own copy of the embedding and reranker models.
        assert Settings(**BARE).celery_worker_concurrency == 1


class TestPayloadValidation:
    def test_a_valid_message_is_accepted(self, worker):
        result = ingestion._run(StubTask(), payload(), "ingest")
        assert result["chunks"] == 9
        assert worker.ingested[0].document_version_id == "ver-1"

    def test_a_message_missing_its_job_id_is_permanent(self, worker):
        body = payload()
        del body["job_id"]
        with pytest.raises(InvalidPayload):
            ingestion._parse(body)

    def test_a_traversing_file_reference_is_refused(self, worker):
        with pytest.raises(InvalidPayload):
            ingestion._parse(payload(file_reference="../../../etc/passwd"))

    def test_an_absolute_file_reference_is_refused(self, worker):
        with pytest.raises(InvalidPayload):
            ingestion._parse(payload(file_reference="/etc/passwd"))

    def test_a_malformed_message_is_never_retried(self, worker, monkeypatch):
        # It will not become valid on a second delivery.
        monkeypatch.setattr(runtime, "context", lambda *a, **k: worker)
        with pytest.raises(InvalidPayload):
            ingestion._parse({"nonsense": True})


class TestRetryPolicy:
    def _worker_with(self, monkeypatch, error: Exception) -> StubPipeline:
        pipeline = StubPipeline(error=error)
        context = type("Ctx", (), {"settings": Settings(**BARE), "pipeline": pipeline})()
        monkeypatch.setattr(runtime, "context", lambda *a, **k: context)
        return pipeline

    def test_a_transient_failure_is_retried(self, monkeypatch):
        self._worker_with(monkeypatch, VectorStoreUnavailable("qdrant down"))
        with pytest.raises(Retried):
            ingestion._run(StubTask(), payload(), "ingest")

    def test_a_permanent_failure_is_not_retried(self, monkeypatch):
        pipeline = self._worker_with(monkeypatch, DocumentNotFound("gone"))
        result = ingestion._run(StubTask(), payload(), "ingest")

        assert result["failed"] is True
        assert result["error_code"] == "DOCUMENT_NOT_FOUND"
        assert len(pipeline.failures) == 1

    def test_a_dimension_mismatch_is_not_retried(self, monkeypatch):
        pipeline = self._worker_with(monkeypatch, EmbeddingDimensionMismatch("384 into 768"))
        result = ingestion._run(StubTask(), payload(), "ingest")
        assert result["error_code"] == "EMBEDDING_DIMENSION_MISMATCH"
        assert pipeline.failures

    def test_retries_do_not_go_on_for_ever(self, monkeypatch):
        # At the ceiling, the transient failure is reported and finished.
        pipeline = self._worker_with(monkeypatch, VectorStoreUnavailable("down"))
        settings = Settings(**BARE)
        result = ingestion._run(
            StubTask(retries=settings.celery_task_max_retries), payload(), "ingest"
        )
        assert result["failed"] is True
        assert pipeline.failures

    def test_the_backoff_ceiling_grows_and_is_capped(self, monkeypatch):
        """The window a retry is drawn from doubles, and stops at the cap.

        Asserted on the ceiling rather than on the delays themselves, because
        the delays are jittered — see the next test. Monotonically increasing
        waits would mean no jitter, which is the property this pair is really
        checking for.
        """
        self._worker_with(monkeypatch, VectorStoreUnavailable("down"))
        settings = Settings(**BARE)

        # Draw the top of the range every time, so what is measured is the
        # ceiling and not the roll of the dice.
        monkeypatch.setattr(ingestion.random, "uniform", lambda _low, high: high)

        ceilings = []
        # Only attempts below max_retries are retried at all; past that the run
        # is reported failed and no countdown is produced.
        for attempt in range(settings.celery_task_max_retries):
            try:
                ingestion._run(StubTask(retries=attempt), payload(), "ingest")
            except Retried as retried:
                ceilings.append(retried.countdown)

        base = settings.celery_retry_backoff
        assert ceilings == [
            min(base * (2**attempt), settings.celery_retry_backoff_max)
            for attempt in range(settings.celery_task_max_retries)
        ]
        assert ceilings == sorted(ceilings)
        assert max(ceilings) <= settings.celery_retry_backoff_max

    def test_retries_are_jittered_so_a_queue_does_not_come_back_at_once(self, monkeypatch):
        """Every document queued behind one outage must not retry in lockstep.

        Without jitter a Qdrant restart brings the whole backlog back at the
        same instant, and the retry storm is what keeps the dependency down.
        """
        self._worker_with(monkeypatch, VectorStoreUnavailable("down"))

        settings = Settings(**BARE)
        attempt = settings.celery_task_max_retries - 1

        delays = set()
        for _ in range(20):
            try:
                # The same attempt number every time: any spread in the result
                # is jitter, not the exponent.
                ingestion._run(StubTask(retries=attempt), payload(), "ingest")
            except Retried as retried:
                delays.add(retried.countdown)

        assert len(delays) > 1, "identical delays mean the retries are not jittered"
        ceiling = min(
            settings.celery_retry_backoff * (2**attempt),
            settings.celery_retry_backoff_max,
        )
        assert all(0 <= delay <= ceiling for delay in delays)

    def test_the_backend_is_not_told_about_a_failure_that_will_be_retried(self, monkeypatch):
        # A job about to be retried is still running; saying FAILED would have
        # an operator chasing a document that is going to fix itself.
        pipeline = self._worker_with(monkeypatch, VectorStoreUnavailable("down"))
        with pytest.raises(Retried):
            ingestion._run(StubTask(), payload(), "ingest")
        assert pipeline.failures == []


class TestOperations:
    def test_reindex_runs_the_same_workflow_against_the_same_version(self, worker):
        result = ingestion._run(StubTask(), payload(operation="reindex"), "reindex")
        assert result["operation"] == "reindex"
        # Same version id — a reindex rebuilds in place rather than forking a
        # new edition, which is what keeps the point ids stable.
        assert worker.ingested[0].document_version_id == "ver-1"

    def test_delete_calls_the_delete_path(self, worker):
        result = ingestion._run(StubTask(), payload(operation="delete"), "delete")
        assert result["removed"] == 9
        assert worker.deleted[0].document_id == "doc-1"

    def test_a_delete_that_removes_nothing_is_still_a_success(self, monkeypatch):
        class EmptyPipeline(StubPipeline):
            async def delete(self, request):
                return 0

        pipeline = EmptyPipeline()
        context = type("Ctx", (), {"settings": Settings(**BARE), "pipeline": pipeline})()
        monkeypatch.setattr(runtime, "context", lambda *a, **k: context)

        result = ingestion._run(StubTask(), payload(operation="delete"), "delete")
        assert result["removed"] == 0
        assert "failed" not in result
