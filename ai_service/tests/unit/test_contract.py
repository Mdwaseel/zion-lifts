"""The wire contract with Django, pinned from this side.

Django and ai_service share no code — that is the point of the architecture, and
it is also its one weakness: nothing but agreement keeps the two message shapes
in step, and a field renamed on one side fails at runtime, in production, inside
a Celery task.

So both sides pin the shape against a literal list. The field names below are
written out rather than derived from the models, because a test that reads the
model it is checking cannot notice the model changing. The mirror of this file
is ``backend/apps/knowledge/tests/test_boundary.py``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas.document import IngestionReport, IngestionRequest
from app.core.constants import DocumentStatus, JobOperation

# Exactly what backend/apps/knowledge/dispatch.py:build_payload emits.
DJANGO_SENDS = {
    "request_id",
    "job_id",
    "document_id",
    "document_version_id",
    "knowledge_base_id",
    "file_reference",
    "content_hash",
    "embedding_model",
    "embedding_model_version",
    "operation",
}

# Exactly what backend/apps/knowledge/api/serializers.py:IngestionReportSerializer
# will accept.
DJANGO_ACCEPTS = {
    "job_id",
    "document_id",
    "document_version_id",
    "stage",
    "progress",
    "page_count",
    "chunk_count",
    "embedding_model",
    "embedding_model_version",
    "embedding_dimension",
    "collection",
    "error_code",
    "error_message",
}

# Django's DocumentState.choices, written out. A stage this service invents
# would be rejected at the callback with a 400 nobody is watching for.
DJANGO_STATES = {
    "uploaded",
    "processing",
    "extracting",
    "chunking",
    "embedding",
    "indexing",
    "ready",
    "failed",
    "deleting",
    "deleted",
}

DJANGO_JOB_TYPES = {"ingest", "reindex", "delete"}


def full_payload() -> dict:
    return {
        "request_id": "req-abc123",
        "job_id": "j",
        "document_id": "d",
        "document_version_id": "v",
        "knowledge_base_id": "k",
        "file_reference": "knowledge/d/v1.pdf",
        "content_hash": "a" * 64,
        "embedding_model": "m",
        "embedding_model_version": "v1",
        "operation": "ingest",
    }


class TestRequestContract:
    def test_everything_django_sends_is_understood(self):
        request = IngestionRequest.model_validate(full_payload())
        assert request.job_id == "j"
        assert request.operation is JobOperation.INGEST

    def test_the_correlation_id_survives_the_queue(self):
        # The whole point of carrying it: one id links the browser request, the
        # Django log lines, the queue message and everything the worker writes.
        assert IngestionRequest.model_validate(full_payload()).request_id == "req-abc123"

    def test_a_message_without_a_correlation_id_is_still_valid(self):
        # A run started by a management command has no originating request. The
        # worker falls back to the job id rather than refusing the work.
        body = full_payload()
        del body["request_id"]
        assert IngestionRequest.model_validate(body).request_id == ""

    def test_no_field_is_required_that_django_does_not_send(self):
        required = {
            name for name, field in IngestionRequest.model_fields.items() if field.is_required()
        }
        assert required <= DJANGO_SENDS, f"the worker demands {required - DJANGO_SENDS}"

    def test_the_identifiers_django_relies_on_are_all_required(self):
        # These four are what the backend uses to verify a report describes a
        # real job. Any of them optional would let a message through with a
        # missing link in that chain.
        required = {
            name for name, field in IngestionRequest.model_fields.items() if field.is_required()
        }
        assert {"job_id", "document_id", "document_version_id", "knowledge_base_id"} <= required

    def test_an_unknown_extra_field_does_not_break_an_older_worker(self):
        # Django adding a field must not stop a worker that has not been
        # redeployed yet — the two are deployed separately by design.
        body = full_payload() | {"something_new": "value"}
        assert IngestionRequest.model_validate(body).job_id == "j"

    def test_a_traversing_reference_is_refused_at_the_schema(self):
        for bad in ("../../etc/passwd", "/etc/passwd", "\\\\server\\share"):
            with pytest.raises(ValidationError):
                IngestionRequest.model_validate(full_payload() | {"file_reference": bad})


class TestReportContract:
    def test_every_field_reported_is_one_django_accepts(self):
        assert set(IngestionReport.model_fields) == DJANGO_ACCEPTS

    def test_a_full_report_serialises_to_json_safe_values(self):
        import json

        report = IngestionReport(
            job_id="j",
            document_id="d",
            document_version_id="v",
            stage=DocumentStatus.READY,
            progress=100,
            page_count=3,
            chunk_count=9,
            embedding_model="m",
            embedding_model_version="v1",
            embedding_dimension=384,
            collection="kb_k__m_v1",
        )
        body = report.model_dump(exclude_none=True, mode="json")
        json.dumps(body)  # raises if anything is not serialisable
        assert set(body) <= DJANGO_ACCEPTS

    def test_the_stage_vocabulary_matches_djangos(self):
        assert {str(state) for state in DocumentStatus} == DJANGO_STATES

    def test_the_operation_vocabulary_matches_djangos(self):
        assert {str(op) for op in JobOperation} == DJANGO_JOB_TYPES

    def test_a_progress_value_stays_within_the_range_django_stores(self):
        # IngestionJob.progress is a PositiveSmallIntegerField validated 0-100.
        with pytest.raises(ValidationError):
            IngestionReport(
                job_id="j",
                document_id="d",
                document_version_id="v",
                stage=DocumentStatus.EMBEDDING,
                progress=101,
            )
