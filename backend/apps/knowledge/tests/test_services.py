"""The lifecycle as operations: upload, replace, reindex, retry, delete."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.knowledge import dispatch
from apps.knowledge.models import DocumentVersion, IngestionJob, JobStatus, JobType
from apps.knowledge.services import document_service, job_service, version_service
from apps.knowledge.states import DocumentState, InvalidTransition

from .base import MINIMAL_PDF, KnowledgeTestCase, patched_dispatch

S = DocumentState


class CreateDocumentTests(KnowledgeTestCase):
    def test_uploading_creates_a_document_a_version_and_a_job(self):
        with self.captured_dispatch() as sender:
            document, version, job = document_service.create_document(
                knowledge_base=self.base, upload=self.upload(), created_by=self.staff
            )

        self.assertEqual(document.knowledge_base_id, self.base.id)
        self.assertEqual(document.created_by_id, self.staff.id)
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.content_hash, version.content_hash.lower())
        self.assertIsNotNone(job)
        self.assertEqual(job.job_type, JobType.INGEST)
        sender.assert_called_once()

    def test_the_document_and_version_both_enter_processing(self):
        with self.captured_dispatch():
            document, version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )
        document.refresh_from_db()
        version.refresh_from_db()
        self.assertEqual(document.status, S.PROCESSING)
        self.assertEqual(version.status, S.PROCESSING)

    def test_the_name_defaults_to_the_sanitised_filename(self):
        with self.captured_dispatch():
            document, _, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload("../../etc/passwd.pdf")
            )
        self.assertEqual(document.name, "passwd.pdf")

    def test_the_stored_path_is_built_from_ids_not_from_the_upload_name(self):
        with self.captured_dispatch():
            _, version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload("../../evil.pdf")
            )
        self.assertTrue(version.file.name.startswith("knowledge/"))
        self.assertNotIn("..", version.file.name)

    def test_a_bad_file_creates_nothing(self):
        from .base import raw_upload

        with self.assertRaises(ValidationError):
            document_service.create_document(
                knowledge_base=self.base, upload=raw_upload("x.pdf", b"\x7fELF\x00")
            )
        self.assertEqual(self.base.documents.count(), 0)

    def test_the_embedding_model_is_stamped_at_upload(self):
        # Recorded per version so the record stays true after the AI service is
        # reconfigured, rather than being inferred later from current settings.
        with override_settings(
            AI_EMBEDDING_MODEL="test/model", AI_EMBEDDING_MODEL_VERSION="v7"
        ), self.captured_dispatch():
            _, version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )
        self.assertEqual(version.embedding_model, "test/model")
        self.assertEqual(version.embedding_model_version, "v7")


class AddVersionTests(KnowledgeTestCase):
    def setUp(self):
        with self.captured_dispatch():
            self.document, self.first, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )

    def test_new_content_becomes_the_next_version(self):
        with self.captured_dispatch():
            version, job = document_service.add_version(
                self.document, upload=self.upload("policy.pdf", MINIMAL_PDF + b"revised\n")
            )
        self.assertEqual(version.version_number, 2)
        self.assertIsNotNone(job)

    def test_identical_bytes_are_refused(self):
        with self.assertRaises(document_service.DuplicateContent) as caught:
            document_service.add_version(self.document, upload=self.upload())
        self.assertEqual(caught.exception.version.id, self.first.id)
        self.assertEqual(self.document.versions.count(), 1)

    def test_identical_bytes_can_be_forced_through(self):
        with self.captured_dispatch():
            version, _ = document_service.add_version(
                self.document, upload=self.upload(), allow_duplicate=True
            )
        self.assertEqual(version.version_number, 2)
        self.assertEqual(version.content_hash, self.first.content_hash)

    def test_the_live_version_keeps_serving_while_a_new_one_indexes(self):
        self.make_ready(self.first, page_count=3, chunk_count=9, embedding_dimension=384)
        self.document.refresh_from_db()
        self.assertEqual(self.document.active_version_id, self.first.id)

        with self.captured_dispatch():
            document_service.add_version(
                self.document, upload=self.upload("policy.pdf", MINIMAL_PDF + b"v2\n")
            )
        self.document.refresh_from_db()
        # Still answering from version 1 — that is the whole point of versions.
        self.assertEqual(self.document.active_version_id, self.first.id)
        self.assertEqual(self.document.status, S.READY)


class CompletionTests(KnowledgeTestCase):
    def setUp(self):
        with self.captured_dispatch():
            self.document, self.version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )

    def test_completing_publishes_the_version_and_records_its_shape(self):
        self.make_ready(
            self.version,
            page_count=12,
            chunk_count=48,
            embedding_dimension=384,
            collection="kb_x__minilm_v1",
        )
        self.document.refresh_from_db()
        self.version.refresh_from_db()

        self.assertEqual(self.version.status, S.READY)
        self.assertEqual(self.version.page_count, 12)
        self.assertEqual(self.version.chunk_count, 48)
        self.assertEqual(self.version.collection, "kb_x__minilm_v1")
        self.assertEqual(self.document.status, S.READY)
        self.assertEqual(self.document.active_version_id, self.version.id)

    def test_a_first_failure_fails_the_document_too(self):
        version_service.fail_version(self.version, code="pdf_unreadable", message="broken")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, S.FAILED)

    def test_a_failed_reindex_leaves_a_serving_document_alone(self):
        self.make_ready(self.version)

        with self.captured_dispatch():
            second, _ = document_service.add_version(
                self.document, upload=self.upload("policy.pdf", MINIMAL_PDF + b"v2\n")
            )
        version_service.fail_version(second, code="embedding_failed")

        self.document.refresh_from_db()
        # The corpus still works; only the new edition did not. Marking the
        # document FAILED here would hide a working document behind a red flag.
        self.assertEqual(self.document.status, S.READY)
        self.assertEqual(self.document.active_version_id, self.version.id)


class JobQueueingTests(KnowledgeTestCase):
    def setUp(self):
        with self.captured_dispatch():
            self.document, self.version, self.job = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )

    def test_queuing_twice_reuses_the_job_already_in_flight(self):
        # Two workers on one version would race to write the same chunk ids.
        with self.captured_dispatch() as sender:
            again = job_service.queue(self.version)
        self.assertEqual(again.id, self.job.id)
        sender.assert_not_called()

    def test_force_starts_a_second_attempt(self):
        with self.captured_dispatch():
            forced = job_service.queue(self.version, force=True)
        self.assertNotEqual(forced.id, self.job.id)
        self.assertEqual(forced.attempt_count, 2)

    def test_the_task_id_is_decided_before_the_send(self):
        # The row and the message must agree, so a redelivery is recognisable.
        with self.captured_dispatch() as sender:
            job = job_service.queue(self.version, force=True)
        self.assertTrue(job.celery_task_id)
        self.assertEqual(sender.call_args.kwargs["task_id"], job.celery_task_id)

    def test_the_payload_carries_identifiers_and_no_file_bytes(self):
        with self.captured_dispatch() as sender:
            job_service.queue(self.version, force=True)
        payload = sender.call_args.args[1]

        self.assertEqual(payload["document_version_id"], str(self.version.id))
        self.assertEqual(payload["knowledge_base_id"], str(self.base.id))
        self.assertEqual(payload["content_hash"], self.version.content_hash)
        self.assertNotIn("file", payload)
        for value in payload.values():
            self.assertIsInstance(value, str)

    def test_a_broker_failure_is_recorded_rather_than_swallowed(self):
        with self.captured_dispatch(
            side_effect=dispatch.BrokerUnavailable("no broker")
        ):
            job = job_service.queue(self.version, force=True)

        job.refresh_from_db()
        self.version.refresh_from_db()
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertEqual(job.error_code, "broker_unavailable")
        self.assertEqual(self.version.status, S.FAILED)

    def test_reporting_a_stage_moves_the_version_with_the_job(self):
        job_service.report_stage(self.job, S.EXTRACTING, task_id="t-1")
        self.job.refresh_from_db()
        self.version.refresh_from_db()

        self.assertEqual(self.job.current_stage, S.EXTRACTING)
        self.assertEqual(self.job.status, JobStatus.RUNNING)
        self.assertEqual(self.version.status, S.EXTRACTING)


class ReindexRetryDeleteTests(KnowledgeTestCase):
    def setUp(self):
        with self.captured_dispatch():
            self.document, self.version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )

    def _make_ready(self):
        self.make_ready(self.version)
        self.document.refresh_from_db()

    def test_reindex_queues_the_live_version_again(self):
        self._make_ready()
        with self.captured_dispatch() as sender:
            job = document_service.reindex(self.document)
        self.assertEqual(job.job_type, JobType.REINDEX)
        self.assertEqual(job.document_version_id, self.version.id)
        sender.assert_called_once()

    def test_retry_is_refused_unless_the_document_failed(self):
        self._make_ready()
        with self.assertRaises(InvalidTransition):
            document_service.retry(self.document)

    def test_retry_requeues_a_failed_document(self):
        version_service.fail_version(self.version, code="pdf_unreadable")
        self.document.refresh_from_db()

        with self.captured_dispatch():
            job = document_service.retry(self.document)
        self.assertEqual(job.job_type, JobType.INGEST)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, S.PROCESSING)

    def test_deletion_queues_a_job_and_does_not_remove_the_record(self):
        self._make_ready()
        with self.captured_dispatch():
            job = document_service.request_deletion(self.document)

        self.document.refresh_from_db()
        self.assertEqual(job.job_type, JobType.DELETE)
        # The row outlives the request: vectors have to be cleared first, or
        # they become orphans nothing can identify.
        self.assertEqual(self.document.status, S.DELETING)
        self.assertTrue(type(self.document).objects.filter(pk=self.document.pk).exists())

    def test_deleting_something_never_indexed_completes_immediately(self):
        empty = type(self.document).objects.create(
            knowledge_base=self.base, name="Nothing", original_filename="n.pdf"
        )
        job = document_service.request_deletion(empty)
        empty.refresh_from_db()
        self.assertEqual(empty.status, S.DELETED)
        self.assertEqual(job.job_type, JobType.DELETE)


class VersionNumberingTests(KnowledgeTestCase):
    def test_numbers_increase_without_reusing_a_failed_one(self):
        with self.captured_dispatch():
            document, first, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )
            version_service.fail_version(first, code="x")
            second, _ = document_service.add_version(
                document, upload=self.upload("p.pdf", MINIMAL_PDF + b"2")
            )
            third, _ = document_service.add_version(
                document, upload=self.upload("p.pdf", MINIMAL_PDF + b"3")
            )

        self.assertEqual([first.version_number, second.version_number, third.version_number], [1, 2, 3])
        self.assertEqual(DocumentVersion.objects.filter(document=document).count(), 3)

    def test_every_job_is_kept_as_history(self):
        with self.captured_dispatch():
            document, version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )
            job_service.queue(version, force=True)
            job_service.queue(version, force=True)
        # Three failures and one failure are different problems.
        self.assertEqual(IngestionJob.objects.filter(document=document).count(), 3)


class BrokerFailureRecoveryTests(KnowledgeTestCase):
    """A broker outage must leave a document an operator can rescue.

    Regression: the failure path used a queryset `update()`, which set the
    version's status and nothing else. The document stayed PROCESSING, the
    control room showed "Queued" for ever, and Retry — which is only offered
    for a failed document — was never available. The upload was unrecoverable
    from the panel.
    """

    def test_a_broker_outage_fails_the_document_not_just_the_version(self):
        with self.captured_dispatch(side_effect=dispatch.BrokerUnavailable("no broker")):
            document, version, job = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )

        document.refresh_from_db()
        version.refresh_from_db()
        job.refresh_from_db()

        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertEqual(version.status, S.FAILED)
        self.assertEqual(document.status, S.FAILED)

    def test_the_document_can_then_be_retried(self):
        # The point of the fix: the operator has a way out.
        with self.captured_dispatch(side_effect=dispatch.BrokerUnavailable("no broker")):
            document, _, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )
        document.refresh_from_db()

        with self.captured_dispatch() as sender:
            retried = document_service.retry(document)

        self.assertEqual(retried.job_type, JobType.INGEST)
        sender.assert_called_once()

    def test_a_broker_outage_does_not_disturb_a_document_already_serving(self):
        with self.captured_dispatch():
            document, first, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )
        self.make_ready(first)
        document.refresh_from_db()

        with self.captured_dispatch(side_effect=dispatch.BrokerUnavailable("no broker")):
            document_service.add_version(
                document, upload=self.upload("p.pdf", MINIMAL_PDF + b"v2")
            )

        document.refresh_from_db()
        # Version 1 is still answering; only the handover of version 2 failed.
        self.assertEqual(document.status, S.READY)
        self.assertEqual(document.active_version_id, first.id)


    def test_failing_an_already_failed_version_is_tolerated(self):
        # A redelivered failure report, or a second handover that also could not
        # reach the broker. Raising here would blow up inside an on-commit
        # callback, where nothing is watching.
        with self.captured_dispatch(side_effect=dispatch.BrokerUnavailable("no broker")):
            document, version, _ = document_service.create_document(
                knowledge_base=self.base, upload=self.upload()
            )
        version.refresh_from_db()

        version_service.fail_version(version, code="broker_unavailable", message="again")
        version.refresh_from_db()
        self.assertEqual(version.status, S.FAILED)
        self.assertEqual(version.error_message, "again")
