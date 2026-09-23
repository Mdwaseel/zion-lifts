"""The whole lifecycle, from upload to a live version and back again.

This is the acceptance test for the half of the chain Django owns: an upload
becomes a job, the job becomes a message, the worker's reports come back through
the callback, and a version becomes active only when it is genuinely complete.

What it does not cover is deliberate and worth naming: it does not run the real
worker, so no PDF is parsed, no embedding is computed and no vector is written.
Those are exercised on the other side of the boundary, in
``ai_service/tests/unit/test_ingestion_pipeline.py``, and the Redis hop between
them in ``ai_service/tests/integration/test_broker.py``. The seam where the two
meet — the exact fields of the message and the report — is pinned from both
sides, here and in ``ai_service/tests/unit/test_contract.py``.
"""

from __future__ import annotations

from django.test import override_settings

from apps.knowledge.models import JobStatus
from apps.knowledge.services import document_service
from apps.knowledge.states import DocumentState

from .base import MINIMAL_PDF, KnowledgeTestCase

S = DocumentState

REPORT_URL = "/api/internal/knowledge/ingestion-report/"
FILE_URL = "/api/internal/knowledge/documents/file/"
UPLOAD_URL = "/api/admin/knowledge/documents/upload/"
TOKEN = "an-internal-token-of-at-least-32-characters"

# What a real worker reports, in order.
STAGES = (S.EXTRACTING, S.CHUNKING, S.EMBEDDING, S.INDEXING)


@override_settings(AI_SERVICE_INTERNAL_TOKEN=TOKEN)
class EndToEndTests(KnowledgeTestCase):
    """Upload, process, activate — then do it again for a second edition."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    # --- helpers ---------------------------------------------------------

    def upload(self, body: bytes = MINIMAL_PDF):
        with self.captured_dispatch() as sender:
            response = self.client.post(
                UPLOAD_URL,
                {"knowledge_base": str(self.base.id), "file": self.pdf(body)},
            )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json(), sender

    def pdf(self, body: bytes = MINIMAL_PDF):
        from .base import pdf_upload

        return pdf_upload("policy.pdf", body)

    def report(self, ids, stage, **extra):
        payload = {**ids, "stage": stage, **extra}
        return self.client.post(
            REPORT_URL, payload, content_type="application/json",
            HTTP_X_INTERNAL_TOKEN=TOKEN,
        )

    def drive_to_ready(self, ids, *, chunk_count=9, page_count=3, collection="kb_a__m_v1"):
        """Play a successful run through the callback, stage by stage."""
        for stage in STAGES:
            self.assertEqual(self.report(ids, stage).status_code, 200)
        return self.report(
            ids,
            S.READY,
            progress=100,
            page_count=page_count,
            chunk_count=chunk_count,
            embedding_dimension=384,
            collection=collection,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_model_version="v1",
        )

    # --- the path --------------------------------------------------------

    def test_an_upload_becomes_a_queued_message_the_worker_can_act_on(self):
        body, sender = self.upload()

        sender.assert_called_once()
        task_name, payload = sender.call_args.args[0], sender.call_args.args[1]

        self.assertEqual(task_name, "ai_service.ingest_document")
        self.assertEqual(payload["job_id"], body["job"]["id"])
        self.assertEqual(payload["document_version_id"], body["version"]["id"])
        self.assertEqual(payload["knowledge_base_id"], str(self.base.id))
        self.assertEqual(payload["operation"], "ingest")
        # An identifier and a hash — the broker never carries the document.
        self.assertNotIn("file", payload)
        self.assertTrue(payload["file_reference"].startswith("knowledge/"))

    def test_the_worker_can_fetch_exactly_the_file_that_was_uploaded(self):
        body, sender = self.upload()
        reference = sender.call_args.args[1]["file_reference"]

        response = self.client.get(
            FILE_URL, {"reference": reference}, HTTP_X_INTERNAL_TOKEN=TOKEN
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), MINIMAL_PDF)

    def test_a_full_successful_run_ends_with_an_active_version(self):
        body, sender = self.upload()
        ids = {
            "job_id": body["job"]["id"],
            "document_id": body["document"]["id"],
            "document_version_id": body["version"]["id"],
        }

        # Nothing is answerable while it is still being processed.
        document = self.document_from(ids)
        self.assertEqual(document.status, S.PROCESSING)
        self.assertIsNone(document.active_version_id)

        self.assertEqual(self.drive_to_ready(ids).status_code, 200)

        document = self.document_from(ids)
        version = document.versions.get()
        self.assertEqual(document.status, S.READY)
        self.assertEqual(document.active_version_id, version.id)
        self.assertEqual(version.chunk_count, 9)
        self.assertEqual(version.page_count, 3)
        self.assertEqual(version.embedding_dimension, 384)
        self.assertEqual(version.collection, "kb_a__m_v1")
        self.assertEqual(document.jobs.first().status, JobStatus.SUCCEEDED)

    def test_a_second_edition_does_not_disturb_the_first_until_it_is_ready(self):
        """The version acceptance test: v1 keeps answering while v2 processes."""
        body, _ = self.upload()
        ids = {
            "job_id": body["job"]["id"],
            "document_id": body["document"]["id"],
            "document_version_id": body["version"]["id"],
        }
        self.drive_to_ready(ids)

        document = self.document_from(ids)
        first = document.active_version

        # A replacement arrives and starts processing.
        with self.captured_dispatch() as sender:
            second, second_job = document_service.add_version(
                document, upload=self.pdf(MINIMAL_PDF + b"revised\n")
            )
        second_ids = {
            "job_id": str(second_job.id),
            "document_id": str(document.id),
            "document_version_id": str(second.id),
        }
        for stage in STAGES:
            self.report(second_ids, stage)

        # Halfway through v2, v1 is still the edition answering questions.
        document.refresh_from_db()
        self.assertEqual(document.status, S.READY)
        self.assertEqual(document.active_version_id, first.id)
        second.refresh_from_db()
        self.assertEqual(second.status, S.INDEXING)

        # v2 finishes, and only now takes over.
        self.drive_to_ready(second_ids, chunk_count=12, collection="kb_a__m_v1")

        document.refresh_from_db()
        self.assertEqual(document.active_version_id, second.id)
        # v1 is kept: it is the rollback target and the history.
        self.assertEqual(document.versions.count(), 2)
        first.refresh_from_db()
        self.assertEqual(first.status, S.READY)

    def test_a_failed_second_edition_leaves_the_first_serving(self):
        body, _ = self.upload()
        ids = {
            "job_id": body["job"]["id"],
            "document_id": body["document"]["id"],
            "document_version_id": body["version"]["id"],
        }
        self.drive_to_ready(ids)
        document = self.document_from(ids)
        first = document.active_version

        with self.captured_dispatch():
            second, second_job = document_service.add_version(
                document, upload=self.pdf(MINIMAL_PDF + b"broken\n")
            )
        self.report(
            {
                "job_id": str(second_job.id),
                "document_id": str(document.id),
                "document_version_id": str(second.id),
            },
            S.FAILED,
            error_code="PDF_EXTRACTION_FAILED",
            error_message="no text layer",
        )

        document.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(second.status, S.FAILED)
        self.assertEqual(second.error_code, "PDF_EXTRACTION_FAILED")
        # A failed replacement is a failed job, not a broken document.
        self.assertEqual(document.status, S.READY)
        self.assertEqual(document.active_version_id, first.id)

    def test_reindex_rebuilds_the_same_version_in_place(self):
        body, _ = self.upload()
        ids = {
            "job_id": body["job"]["id"],
            "document_id": body["document"]["id"],
            "document_version_id": body["version"]["id"],
        }
        self.drive_to_ready(ids)
        document = self.document_from(ids)
        version_id = document.active_version_id

        with self.captured_dispatch() as sender:
            job = document_service.reindex(document)

        task_name, payload = sender.call_args.args[0], sender.call_args.args[1]
        self.assertEqual(task_name, "ai_service.reindex_document")
        self.assertEqual(payload["operation"], "reindex")
        # The same version, so the worker writes the same point ids and
        # replaces its own chunks rather than adding a second copy.
        self.assertEqual(payload["document_version_id"], str(version_id))
        self.assertEqual(payload["job_id"], str(job.id))

    def test_delete_removes_the_vectors_before_the_record(self):
        body, _ = self.upload()
        ids = {
            "job_id": body["job"]["id"],
            "document_id": body["document"]["id"],
            "document_version_id": body["version"]["id"],
        }
        self.drive_to_ready(ids)
        document = self.document_from(ids)

        with self.captured_dispatch() as sender:
            job = document_service.request_deletion(document)

        self.assertEqual(sender.call_args.args[0], "ai_service.delete_document")
        document.refresh_from_db()
        self.assertEqual(document.status, S.DELETING)

        delete_ids = {
            "job_id": str(job.id),
            "document_id": str(document.id),
            "document_version_id": str(document.active_version_id),
        }
        self.report(delete_ids, S.DELETED, progress=100)

        document.refresh_from_db()
        self.assertEqual(document.status, S.DELETED)
        # The row outlives its vectors: what happened is worth keeping.
        self.assertTrue(type(document).objects.filter(pk=document.pk).exists())

    # --- helper ----------------------------------------------------------

    def document_from(self, ids):
        from apps.knowledge.models import Document

        return Document.objects.select_related("active_version").get(pk=ids["document_id"])
