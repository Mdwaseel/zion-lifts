"""The worker's callback: who may call it, and what it will accept.

This endpoint is the only route by which a process outside Django changes a
document's state, so the tests below are mostly about refusal — a wrong token, a
report whose identifiers do not describe each other, a message that arrived
twice or arrived late.
"""

from __future__ import annotations

import uuid

from django.test import override_settings

from apps.knowledge.models import Document, IngestionJob, JobStatus
from apps.knowledge.services import document_service
from apps.knowledge.states import DocumentState

from .base import MINIMAL_PDF, KnowledgeTestCase

S = DocumentState

REPORT_URL = "/api/internal/knowledge/ingestion-report/"
FILE_URL = "/api/internal/knowledge/documents/file/"
TOKEN = "an-internal-token-of-at-least-32-characters"


@override_settings(AI_SERVICE_INTERNAL_TOKEN=TOKEN)
class ReportEndpointTestCase(KnowledgeTestCase):
    """A document mid-ingestion, and a helper to report against it."""

    def setUp(self):
        super().setUp()
        with self.captured_dispatch():
            self.document, self.version, self.job = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )

    def report(self, stage, *, token=TOKEN, **extra):
        payload = {
            "job_id": str(self.job.id),
            "document_id": str(self.document.id),
            "document_version_id": str(self.version.id),
            "stage": stage,
            "progress": 50,
            **extra,
        }
        headers = {"HTTP_X_INTERNAL_TOKEN": token} if token else {}
        return self.client.post(
            REPORT_URL, payload, content_type="application/json", **headers
        )


class AuthenticationTests(ReportEndpointTestCase):
    def test_a_valid_token_is_accepted(self):
        self.assertEqual(self.report(S.EXTRACTING).status_code, 200)

    def test_a_missing_token_is_refused(self):
        self.assertEqual(self.report(S.EXTRACTING, token=None).status_code, 403)

    def test_a_wrong_token_is_refused(self):
        self.assertEqual(self.report(S.EXTRACTING, token="not-the-token").status_code, 403)

    def test_a_token_that_is_a_prefix_of_the_real_one_is_refused(self):
        self.assertEqual(self.report(S.EXTRACTING, token=TOKEN[:-1]).status_code, 403)

    @override_settings(AI_SERVICE_INTERNAL_TOKEN="")
    def test_an_unconfigured_backend_refuses_everything(self):
        # The safe failure: a deployment that forgot the token stops ingesting
        # rather than accepting anonymous writes to its document pipeline.
        self.assertEqual(self.report(S.EXTRACTING).status_code, 403)

    def test_a_user_session_does_not_open_the_internal_route(self):
        # Staff credentials are not service credentials.
        self.client.force_login(self.staff)
        self.assertEqual(self.report(S.EXTRACTING, token=None).status_code, 403)

    def test_the_route_is_not_reachable_under_the_staff_prefix(self):
        # The internal urlconf is a separate module precisely so the staff
        # router is not mounted where the token is the only guard.
        response = self.client.get("/api/internal/knowledge/documents/")
        self.assertEqual(response.status_code, 404)


class PayloadValidationTests(ReportEndpointTestCase):
    def test_a_malformed_payload_is_rejected(self):
        response = self.client.post(
            REPORT_URL,
            {"job_id": "not-a-uuid", "stage": "nonsense"},
            content_type="application/json",
            HTTP_X_INTERNAL_TOKEN=TOKEN,
        )
        self.assertEqual(response.status_code, 400)

    def test_an_unknown_stage_is_rejected(self):
        self.assertEqual(self.report("teleporting").status_code, 400)

    def test_a_failure_without_an_error_code_is_rejected(self):
        # A FAILED report that does not say why is a job an operator cannot act
        # on, so it is refused at the edge rather than stored half-empty.
        self.assertEqual(self.report(S.FAILED).status_code, 400)

    def test_an_unknown_job_is_a_404(self):
        response = self.report(S.EXTRACTING, job_id=str(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)

    def test_a_job_document_mismatch_is_refused(self):
        # Holding one valid job id must not let a caller write onto another
        # document.
        other = Document.objects.create(
            knowledge_base=self.base, name="Other", original_filename="o.pdf"
        )
        response = self.report(S.EXTRACTING, document_id=str(other.id))
        self.assertEqual(response.status_code, 404)

    def test_a_job_version_mismatch_is_refused(self):
        response = self.report(S.EXTRACTING, document_version_id=str(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)


class ProgressTests(ReportEndpointTestCase):
    def test_a_stage_report_moves_the_job_and_the_version(self):
        self.assertEqual(self.report(S.EXTRACTING).status_code, 200)

        self.job.refresh_from_db()
        self.version.refresh_from_db()
        self.assertEqual(self.job.status, JobStatus.RUNNING)
        self.assertEqual(self.job.current_stage, S.EXTRACTING)
        self.assertEqual(self.version.status, S.EXTRACTING)

    def test_the_same_stage_twice_does_not_corrupt_anything(self):
        self.report(S.EXTRACTING)
        response = self.report(S.EXTRACTING)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "progress_refreshed")
        self.version.refresh_from_db()
        self.assertEqual(self.version.status, S.EXTRACTING)

    def test_counts_are_stored_as_they_are_measured(self):
        self.report(S.EXTRACTING, page_count=124)
        self.report(S.CHUNKING, page_count=124, chunk_count=432)
        self.version.refresh_from_db()
        self.assertEqual(self.version.page_count, 124)
        self.assertEqual(self.version.chunk_count, 432)

    def test_an_out_of_order_report_has_its_counts_ignored_too(self):
        # Not just its stage. A message that arrived out of sequence may be
        # from a superseded attempt, and half-believing it — taking the numbers
        # while rejecting the transition — would describe this version with
        # another run's measurements.
        self.report(S.EXTRACTING)
        self.report(S.INDEXING, page_count=999, chunk_count=999)
        self.version.refresh_from_db()
        self.assertIsNone(self.version.page_count)
        self.assertIsNone(self.version.chunk_count)

    def test_an_out_of_order_stage_is_ignored(self):
        # INDEXING cannot follow PROCESSING; the stored state came from a
        # message already accepted and is the one to keep.
        self.report(S.EXTRACTING)
        response = self.report(S.INDEXING)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "out_of_order")
        self.version.refresh_from_db()
        self.assertEqual(self.version.status, S.EXTRACTING)


class CompletionTests(ReportEndpointTestCase):
    def _walk(self):
        for stage in (S.EXTRACTING, S.CHUNKING, S.EMBEDDING, S.INDEXING):
            self.report(stage)

    def test_ready_activates_the_version(self):
        self._walk()
        response = self.report(
            S.READY,
            progress=100,
            page_count=12,
            chunk_count=48,
            embedding_dimension=384,
            collection="kb_x__minilm_v1",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_model_version="v1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "activated")

        self.document.refresh_from_db()
        self.version.refresh_from_db()
        self.job.refresh_from_db()

        self.assertEqual(self.version.status, S.READY)
        self.assertEqual(self.version.collection, "kb_x__minilm_v1")
        self.assertEqual(self.version.embedding_dimension, 384)
        self.assertEqual(self.document.status, S.READY)
        self.assertEqual(self.document.active_version_id, self.version.id)
        self.assertEqual(self.job.status, JobStatus.SUCCEEDED)
        self.assertEqual(self.job.progress, 100)

    def test_the_embedding_actually_used_overwrites_what_was_stamped(self):
        # If a fallback model answered, the record must name it — the collection
        # is named after that model, and a version pointing at another one
        # describes an index that does not hold its vectors.
        self._walk()
        self.report(
            S.READY,
            progress=100,
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_model_version="v2",
            collection="kb_x__bge_small_en_v1_5_v2",
        )
        self.version.refresh_from_db()
        self.assertEqual(self.version.embedding_model, "BAAI/bge-small-en-v1.5")
        self.assertEqual(self.version.embedding_model_version, "v2")

    def test_a_duplicate_ready_report_changes_nothing(self):
        self._walk()
        self.report(S.READY, progress=100, chunk_count=48)
        response = self.report(S.READY, progress=100, chunk_count=48)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "duplicate")
        self.assertEqual(
            IngestionJob.objects.filter(status=JobStatus.SUCCEEDED).count(), 1
        )

    def test_a_late_progress_report_cannot_reopen_a_finished_job(self):
        # The failure this guards against: a straggler from a superseded attempt
        # dragging a live document back into EMBEDDING.
        self._walk()
        self.report(S.READY, progress=100)

        response = self.report(S.EMBEDDING)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "stale_job_finished")

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, S.READY)
        self.assertEqual(self.document.active_version_id, self.version.id)


class FailureTests(ReportEndpointTestCase):
    def test_a_failure_report_records_the_code_and_the_message(self):
        response = self.report(
            S.FAILED,
            error_code="PDF_EXTRACTION_FAILED",
            error_message="no text layer",
        )
        self.assertEqual(response.status_code, 200)

        self.job.refresh_from_db()
        self.version.refresh_from_db()
        self.assertEqual(self.job.status, JobStatus.FAILED)
        self.assertEqual(self.job.error_code, "PDF_EXTRACTION_FAILED")
        self.assertEqual(self.version.status, S.FAILED)

    def test_a_duplicate_failure_report_changes_nothing(self):
        self.report(S.FAILED, error_code="EMBEDDING_FAILED")
        response = self.report(S.FAILED, error_code="EMBEDDING_FAILED")
        self.assertEqual(response.json()["applied"], False)

    def test_a_failed_second_version_leaves_the_live_one_serving(self):
        """The property the whole design exists for."""
        for stage in (S.EXTRACTING, S.CHUNKING, S.EMBEDDING, S.INDEXING):
            self.report(stage)
        self.report(S.READY, progress=100, chunk_count=10)

        with self.captured_dispatch():
            second, second_job = document_service.add_version(
                self.document, upload=self.upload("policy.pdf", MINIMAL_PDF + b"v2\n")
            )

        payload = {
            "job_id": str(second_job.id),
            "document_id": str(self.document.id),
            "document_version_id": str(second.id),
            "stage": S.FAILED,
            "error_code": "EMBEDDING_FAILED",
        }
        self.client.post(
            REPORT_URL, payload, content_type="application/json",
            HTTP_X_INTERNAL_TOKEN=TOKEN,
        )

        self.document.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(second.status, S.FAILED)
        # Version 1 is untouched and still answering.
        self.assertEqual(self.document.status, S.READY)
        self.assertEqual(self.document.active_version_id, self.version.id)


@override_settings(AI_SERVICE_INTERNAL_TOKEN=TOKEN)
class DocumentFileTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        with self.captured_dispatch():
            self.document, self.version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )

    def test_the_worker_can_fetch_a_stored_file(self):
        response = self.client.get(
            FILE_URL,
            {"reference": self.version.file.name},
            HTTP_X_INTERNAL_TOKEN=TOKEN,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), MINIMAL_PDF)

    def test_fetching_requires_the_token(self):
        response = self.client.get(FILE_URL, {"reference": self.version.file.name})
        self.assertEqual(response.status_code, 403)

    def test_an_arbitrary_path_is_not_readable(self):
        # The reference is matched against a real DocumentVersion row, so it
        # cannot be used to walk MEDIA_ROOT.
        for probe in ("../../backend/.env", "knowledge/../../secret.pdf", "db.sqlite3"):
            response = self.client.get(
                FILE_URL, {"reference": probe}, HTTP_X_INTERNAL_TOKEN=TOKEN
            )
            self.assertEqual(response.status_code, 404, probe)

    def test_a_missing_reference_is_a_400(self):
        response = self.client.get(FILE_URL, HTTP_X_INTERNAL_TOKEN=TOKEN)
        self.assertEqual(response.status_code, 400)
