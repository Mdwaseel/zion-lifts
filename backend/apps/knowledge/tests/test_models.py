"""Models, constraints, and the transitions as the records enforce them."""

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from apps.knowledge.models import (
    Document,
    DocumentVersion,
    IngestionJob,
    JobStatus,
    JobType,
    KnowledgeBase,
)
from apps.knowledge.states import DocumentState, InvalidTransition

from .base import MINIMAL_PDF, KnowledgeTestCase

S = DocumentState


class KnowledgeBaseTests(KnowledgeTestCase):
    def test_slug_is_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            KnowledgeBase.objects.create(name="Another", slug="product-manuals")

    def test_a_base_is_active_by_default(self):
        self.assertTrue(KnowledgeBase.objects.create(name="Policies", slug="policies").is_active)

    def test_id_is_a_uuid_not_a_sequence(self):
        # These ids travel to another service and into vector payloads, where a
        # guessable sequential integer would be both an enumeration surface and
        # unsafe to compare across environments.
        self.assertEqual(len(str(self.base.id)), 36)
        self.assertNotEqual(str(self.base.id), "1")


class DocumentVersionConstraintTests(KnowledgeTestCase):
    def setUp(self):
        self.document = Document.objects.create(
            knowledge_base=self.base, name="Warranty", original_filename="warranty.pdf"
        )

    def _version(self, number: int, content_hash: str = "abc123") -> DocumentVersion:
        return DocumentVersion.objects.create(
            document=self.document,
            version_number=number,
            content_hash=content_hash,
            file=SimpleUploadedFile(f"v{number}.pdf", MINIMAL_PDF),
        )

    def test_version_numbers_are_unique_per_document(self):
        self._version(1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._version(1, content_hash="different")

    def test_the_same_number_may_exist_on_another_document(self):
        other = Document.objects.create(
            knowledge_base=self.base, name="Other", original_filename="other.pdf"
        )
        self._version(1)
        DocumentVersion.objects.create(
            document=other, version_number=1, content_hash="x", file=SimpleUploadedFile("o.pdf", MINIMAL_PDF)
        )
        self.assertEqual(DocumentVersion.objects.filter(version_number=1).count(), 2)

    def test_versions_are_ordered_newest_first(self):
        self._version(1, "h1")
        self._version(2, "h2")
        self._version(3, "h3")
        self.assertEqual(
            [v.version_number for v in self.document.versions.all()], [3, 2, 1]
        )

    def test_counts_start_null_not_zero(self):
        # "Not processed yet" and "genuinely has no pages" must stay
        # distinguishable, or a stuck document looks like an empty one.
        version = self._version(1)
        self.assertIsNone(version.page_count)
        self.assertIsNone(version.chunk_count)


class DocumentTransitionTests(KnowledgeTestCase):
    def setUp(self):
        self.document = Document.objects.create(
            knowledge_base=self.base, name="Warranty", original_filename="warranty.pdf"
        )

    def test_a_new_document_starts_uploaded(self):
        self.assertEqual(self.document.status, S.UPLOADED)

    def test_transition_to_persists(self):
        self.document.transition_to(S.PROCESSING)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, S.PROCESSING)

    def test_an_illegal_transition_raises_and_changes_nothing(self):
        with self.assertRaises(InvalidTransition):
            self.document.transition_to(S.READY)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, S.UPLOADED)

    def test_publishing_a_version_makes_it_active_and_the_document_ready(self):
        version = DocumentVersion.objects.create(
            document=self.document,
            version_number=1,
            content_hash="h",
            status=S.READY,
            file=SimpleUploadedFile("v1.pdf", MINIMAL_PDF),
        )
        self.document.transition_to(S.PROCESSING)
        self.document.publish_version(version)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, S.READY)
        self.assertEqual(self.document.active_version_id, version.id)
        self.assertTrue(version.is_active)

    def test_publishing_a_version_that_is_not_ready_is_refused(self):
        version = DocumentVersion.objects.create(
            document=self.document,
            version_number=1,
            content_hash="h",
            status=S.EMBEDDING,
            file=SimpleUploadedFile("v1.pdf", MINIMAL_PDF),
        )
        with self.assertRaises(InvalidTransition):
            self.document.publish_version(version)
        self.document.refresh_from_db()
        self.assertIsNone(self.document.active_version_id)

    def test_publishing_a_version_of_another_document_is_refused(self):
        other = Document.objects.create(
            knowledge_base=self.base, name="Other", original_filename="o.pdf"
        )
        version = DocumentVersion.objects.create(
            document=other,
            version_number=1,
            content_hash="h",
            status=S.READY,
            file=SimpleUploadedFile("v1.pdf", MINIMAL_PDF),
        )
        with self.assertRaises(ValueError):
            self.document.publish_version(version)

    def test_storage_path_is_the_live_editions_file(self):
        self.assertEqual(self.document.storage_path, "")
        version = DocumentVersion.objects.create(
            document=self.document,
            version_number=1,
            content_hash="h",
            status=S.READY,
            file=SimpleUploadedFile("v1.pdf", MINIMAL_PDF),
        )
        self.document.transition_to(S.PROCESSING)
        self.document.publish_version(version)
        self.assertIn(str(self.document.id), self.document.storage_path)


class IngestionJobTests(KnowledgeTestCase):
    def setUp(self):
        self.document = Document.objects.create(
            knowledge_base=self.base, name="Warranty", original_filename="warranty.pdf"
        )
        self.version = DocumentVersion.objects.create(
            document=self.document,
            version_number=1,
            content_hash="h",
            file=SimpleUploadedFile("v1.pdf", MINIMAL_PDF),
        )

    def _job(self) -> IngestionJob:
        return IngestionJob.objects.create(
            document=self.document, document_version=self.version, job_type=JobType.INGEST
        )

    def test_a_new_job_is_queued_with_no_progress(self):
        job = self._job()
        self.assertEqual(job.status, JobStatus.QUEUED)
        self.assertEqual(job.progress, 0)
        self.assertIsNone(job.started_at)

    def test_marking_running_records_the_stage_its_progress_and_the_start(self):
        job = self._job()
        job.mark_running(S.EMBEDDING, task_id="task-1")
        job.refresh_from_db()

        self.assertEqual(job.status, JobStatus.RUNNING)
        self.assertEqual(job.current_stage, S.EMBEDDING)
        self.assertEqual(job.celery_task_id, "task-1")
        self.assertGreater(job.progress, 0)
        self.assertIsNotNone(job.started_at)

    def test_the_start_time_is_not_reset_by_later_stages(self):
        job = self._job()
        job.mark_running(S.EXTRACTING)
        first = job.started_at
        job.mark_running(S.INDEXING)
        job.refresh_from_db()
        self.assertEqual(job.started_at, first)

    def test_succeeding_finishes_at_one_hundred(self):
        job = self._job()
        job.mark_running(S.EXTRACTING)
        job.mark_succeeded()
        job.refresh_from_db()

        self.assertEqual(job.status, JobStatus.SUCCEEDED)
        self.assertEqual(job.progress, 100)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNotNone(job.duration_seconds)

    def test_failing_records_a_code_and_truncates_the_message(self):
        job = self._job()
        job.mark_failed("pdf_unreadable", "x" * 9000)
        job.refresh_from_db()

        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertEqual(job.error_code, "pdf_unreadable")
        self.assertLessEqual(len(job.error_message), 4000)

    def test_progress_cannot_exceed_one_hundred(self):
        job = self._job()
        job.progress = 150
        with self.assertRaises(Exception):
            job.full_clean()
