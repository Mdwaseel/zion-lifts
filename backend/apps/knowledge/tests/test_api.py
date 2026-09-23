"""The HTTP surface: who may reach it, and what it does with a file."""

from __future__ import annotations

from apps.knowledge.models import Document, JobType
from apps.knowledge.states import DocumentState

from .base import MINIMAL_PDF, KnowledgeTestCase, big_pdf, raw_upload

S = DocumentState

BASES = "/api/admin/knowledge/bases/"
DOCUMENTS = "/api/admin/knowledge/documents/"
UPLOAD = "/api/admin/knowledge/documents/upload/"


class PermissionTests(KnowledgeTestCase):
    def test_an_anonymous_caller_is_refused(self):
        for url in (BASES, DOCUMENTS):
            self.assertIn(self.client.get(url).status_code, (401, 403), url)

    def test_a_signed_in_non_staff_user_is_refused(self):
        from django.contrib.auth import get_user_model

        visitor = get_user_model().objects.create_user(
            username="visitor", email="v@zionlifts.test", password="a-long-enough-passphrase"
        )
        self.client.force_login(visitor)
        self.assertEqual(self.client.get(DOCUMENTS).status_code, 403)

    def test_staff_may_list(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(DOCUMENTS).status_code, 200)

    def test_upload_is_refused_without_staff(self):
        response = self.client.post(
            UPLOAD, {"knowledge_base": str(self.base.id), "file": self.upload()}
        )
        self.assertIn(response.status_code, (401, 403))


class UploadEndpointTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def _post(self, upload, **extra):
        payload = {"knowledge_base": str(self.base.id), "file": upload, **extra}
        with self.captured_dispatch():
            return self.client.post(UPLOAD, payload)

    def test_a_valid_pdf_is_accepted_and_queued(self):
        response = self._post(self.upload())
        self.assertEqual(response.status_code, 201)

        body = response.json()
        self.assertEqual(body["document"]["status"], S.PROCESSING)
        self.assertEqual(body["version"]["version_number"], 1)
        self.assertEqual(body["job"]["job_type"], JobType.INGEST)
        self.assertEqual(Document.objects.count(), 1)

    def test_the_uploader_is_recorded(self):
        self._post(self.upload())
        self.assertEqual(Document.objects.get().created_by_id, self.staff.id)

    def test_a_non_pdf_is_refused_with_a_usable_message(self):
        response = self._post(raw_upload("notes.txt", MINIMAL_PDF, "text/plain"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_a_disguised_binary_is_refused(self):
        response = self._post(raw_upload("payload.pdf", b"\x7fELF" + b"\x00" * 100))
        self.assertEqual(response.status_code, 400)
        self.assertIn("not a PDF", response.json()["detail"])
        self.assertEqual(Document.objects.count(), 0)

    def test_an_empty_file_is_refused(self):
        response = self._post(raw_upload("empty.pdf", b""))
        self.assertEqual(response.status_code, 400)

    def test_an_oversized_file_is_refused(self):
        response = self._post(raw_upload("huge.pdf", big_pdf(26 * 1024 * 1024)))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_an_inactive_knowledge_base_is_refused(self):
        self.base.is_active = False
        self.base.save(update_fields=["is_active"])
        response = self._post(self.upload())
        self.assertEqual(response.status_code, 400)

    def test_documents_cannot_be_created_by_posting_a_row(self):
        # Creating a document means storing a file and queuing work. Leaving
        # POST /documents/ open would let a row exist with neither.
        self.assertEqual(self.client.post(DOCUMENTS, {"name": "x"}).status_code, 405)

    def test_documents_cannot_be_deleted_by_verb(self):
        # Removing a document has to clear its vectors first, so it is an
        # operation with its own endpoint rather than a DELETE.
        self._post(self.upload())
        document = Document.objects.get()
        self.assertEqual(self.client.delete(f"{DOCUMENTS}{document.id}/").status_code, 405)


class DocumentActionTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)
        with self.captured_dispatch():
            self.client.post(
                UPLOAD, {"knowledge_base": str(self.base.id), "file": self.upload()}
            )
        self.document = Document.objects.get()
        self.version = self.document.versions.first()

    def test_status_reports_the_latest_job(self):
        response = self.client.get(f"{DOCUMENTS}{self.document.id}/status/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], S.PROCESSING)
        self.assertIsNotNone(body["job"])

    def test_versions_are_listed_newest_first(self):
        self.make_ready(self.version)
        with self.captured_dispatch():
            self.client.post(
                f"{DOCUMENTS}{self.document.id}/versions/",
                {"file": self.upload("policy.pdf", MINIMAL_PDF + b"v2\n")},
            )
        body = self.client.get(f"{DOCUMENTS}{self.document.id}/versions/").json()
        self.assertEqual([v["version_number"] for v in body], [2, 1])

    def test_uploading_identical_bytes_returns_a_conflict_naming_the_version(self):
        response = self.client.post(
            f"{DOCUMENTS}{self.document.id}/versions/", {"file": self.upload()}
        )
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["code"], "duplicate_content")
        self.assertEqual(body["version"]["version_number"], 1)

    def test_reindex_accepts_and_queues(self):
        self.make_ready(self.version)
        with self.captured_dispatch() as sender:
            response = self.client.post(f"{DOCUMENTS}{self.document.id}/reindex/")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["job_type"], JobType.REINDEX)
        sender.assert_called_once()

    def test_retry_is_refused_while_the_document_is_healthy(self):
        self.make_ready(self.version)
        response = self.client.post(f"{DOCUMENTS}{self.document.id}/retry/")
        self.assertEqual(response.status_code, 409)

    def test_delete_begins_removal_without_dropping_the_record(self):
        self.make_ready(self.version)
        with self.captured_dispatch():
            response = self.client.post(f"{DOCUMENTS}{self.document.id}/delete/")
        self.assertEqual(response.status_code, 202)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, S.DELETING)

    def test_the_list_carries_progress_without_extra_requests(self):
        body = self.client.get(DOCUMENTS).json()
        row = body["results"][0] if isinstance(body, dict) else body[0]
        self.assertIn("latest_job", row)
        self.assertTrue(row["is_processing"])

    def test_listing_can_be_filtered_by_status(self):
        response = self.client.get(DOCUMENTS, {"status": S.READY.value})
        body = response.json()
        rows = body["results"] if isinstance(body, dict) else body
        self.assertEqual(rows, [])


class KnowledgeBaseEndpointTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_bases_are_listed_with_their_counts(self):
        body = self.client.get(BASES).json()
        rows = body["results"] if isinstance(body, dict) else body
        self.assertEqual(rows[0]["document_count"], 0)
        self.assertEqual(rows[0]["ready_count"], 0)

    def test_a_base_can_be_created(self):
        response = self.client.post(
            BASES, {"name": "Service manuals", "slug": "service-manuals"}
        )
        self.assertEqual(response.status_code, 201)

    def test_a_duplicate_slug_is_refused(self):
        response = self.client.post(BASES, {"name": "Another", "slug": self.base.slug})
        self.assertEqual(response.status_code, 400)
