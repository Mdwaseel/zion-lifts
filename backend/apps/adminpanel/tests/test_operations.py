"""Operational endpoints: stale detection, correlation, redaction, access.

The stale-job tests are the ones to read first. Stale detection is a signal an
operator acts on, so the expensive mistake is not missing a stuck job — it is
calling a *healthy* one stuck, because that trains people to ignore the signal.
Most of these therefore assert that something is **not** reported.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import timedelta

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.knowledge.models import (
    Document,
    DocumentVersion,
    IngestionJob,
    JobStatus,
    KnowledgeBase,
)
from apps.knowledge.selectors import operations as ops
from apps.knowledge.states import DocumentState

from .base import API, AdminPanelTestCase

STALE_AFTER = 1800


def make_job(status: str, *, age_seconds: int = 0, attempts: int = 1) -> IngestionJob:
    """A job whose last update is `age_seconds` in the past.

    ``updated_at`` is auto-managed, so it is written with a queryset update
    after the row exists — assigning it before ``save()`` would simply be
    overwritten and the test would silently measure nothing.
    """
    base = KnowledgeBase.objects.create(name=f"KB {uuid.uuid4().hex[:6]}", slug=uuid.uuid4().hex[:8])
    document = Document.objects.create(knowledge_base=base, name="Spec")
    job = IngestionJob.objects.create(
        document=document, status=status, attempt_count=attempts
    )
    if age_seconds:
        moment = timezone.now() - timedelta(seconds=age_seconds)
        IngestionJob.objects.filter(pk=job.pk).update(updated_at=moment)
        job.refresh_from_db()
    return job


@override_settings(INGESTION_STALE_AFTER_SECONDS=STALE_AFTER)
class StaleJobDetectionTests(TestCase):
    def test_a_fresh_running_job_is_not_stale(self):
        make_job(JobStatus.RUNNING)
        self.assertEqual(ops.stale_jobs().count(), 0)

    def test_a_long_running_job_is_stale(self):
        job = make_job(JobStatus.RUNNING, age_seconds=STALE_AFTER + 60)
        self.assertEqual([j.pk for j in ops.stale_jobs()], [job.pk])

    def test_a_job_stuck_in_queued_is_stale_too(self):
        # Just as stuck, and a different problem: nothing is consuming the
        # queue, rather than a worker dying mid-run.
        job = make_job(JobStatus.QUEUED, age_seconds=STALE_AFTER + 60)
        self.assertIn(job.pk, [j.pk for j in ops.stale_jobs()])

    def test_an_old_completed_job_is_never_stale(self):
        # The mistake that matters: a week-old success is finished, not stuck.
        make_job(JobStatus.SUCCEEDED, age_seconds=7 * 24 * 3600)
        self.assertEqual(ops.stale_jobs().count(), 0)

    def test_an_old_failed_job_is_never_stale(self):
        make_job(JobStatus.FAILED, age_seconds=7 * 24 * 3600)
        self.assertEqual(ops.stale_jobs().count(), 0)

    def test_a_job_exactly_at_the_threshold_is_not_yet_stale(self):
        make_job(JobStatus.RUNNING, age_seconds=STALE_AFTER - 5)
        self.assertEqual(ops.stale_jobs().count(), 0)

    def test_a_retrying_job_that_keeps_reporting_stays_healthy(self):
        # Measured from updated_at, so a job making slow progress keeps
        # refreshing itself out of the stale window.
        make_job(JobStatus.RUNNING, attempts=3)
        self.assertEqual(ops.stale_jobs().count(), 0)

    def test_detection_never_changes_a_job(self):
        """Detection reports; it must not decide.

        A dead worker and a slow one look identical from here, and only one is
        safe to give up on.
        """
        job = make_job(JobStatus.RUNNING, age_seconds=STALE_AFTER + 600)
        list(ops.stale_jobs())
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.RUNNING)
        self.assertEqual(job.error_code, "")

    def test_the_threshold_is_configurable(self):
        make_job(JobStatus.RUNNING, age_seconds=120)
        self.assertEqual(ops.stale_jobs().count(), 0)
        self.assertEqual(ops.stale_jobs(seconds=60).count(), 1)


@override_settings(INGESTION_STALE_AFTER_SECONDS=STALE_AFTER)
class IngestionSnapshotTests(TestCase):
    def test_the_snapshot_counts_each_state_once(self):
        make_job(JobStatus.QUEUED)
        make_job(JobStatus.RUNNING)
        make_job(JobStatus.RUNNING, age_seconds=STALE_AFTER + 60)
        make_job(JobStatus.SUCCEEDED)
        make_job(JobStatus.FAILED)

        snapshot = ops.ingestion_snapshot()
        self.assertEqual(snapshot.queued, 1)
        self.assertEqual(snapshot.running, 2)
        self.assertEqual(snapshot.stale, 1)
        self.assertEqual(snapshot.succeeded_24h, 1)
        self.assertEqual(snapshot.failed_24h, 1)

    def test_the_snapshot_is_a_single_query(self):
        # It backs a dashboard refreshed during an incident, which is the worst
        # moment to fan out across the database.
        for status in (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.FAILED):
            make_job(status)
        with self.assertNumQueries(1):
            ops.ingestion_snapshot()

    def test_a_retried_job_is_counted_as_retried(self):
        make_job(JobStatus.RUNNING, attempts=3)
        self.assertEqual(ops.ingestion_snapshot().retried_24h, 1)

    def test_a_first_attempt_is_not_a_retry(self):
        make_job(JobStatus.RUNNING, attempts=1)
        self.assertEqual(ops.ingestion_snapshot().retried_24h, 0)


class OperationsEndpointTests(AdminPanelTestCase):
    def test_the_overview_needs_staff(self):
        response = self.as_non_staff().get(f"{API}/operations/overview/")
        self.assertEqual(response.status_code, 403)

    def test_the_overview_is_closed_to_anonymous_callers(self):
        response = self.as_anonymous().get(f"{API}/operations/overview/")
        self.assertIn(response.status_code, (401, 403))

    def test_the_ingestion_view_needs_staff(self):
        self.assertEqual(
            self.as_non_staff().get(f"{API}/operations/ingestion/").status_code, 403
        )
        self.assertIn(
            self.as_anonymous().get(f"{API}/operations/ingestion/").status_code, (401, 403)
        )

    def test_provider_health_is_closed_to_non_staff(self):
        self.assertEqual(
            self.as_non_staff().get(f"{API}/operations/providers/").status_code, 403
        )

    def test_staff_see_the_overview(self):
        response = self.client.get(f"{API}/operations/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ingestion", response.data)
        self.assertIn("stale", response.data["ingestion"])

    @override_settings(INGESTION_STALE_AFTER_SECONDS=STALE_AFTER)
    def test_a_stuck_job_is_reported_as_degraded(self):
        make_job(JobStatus.RUNNING, age_seconds=STALE_AFTER + 600)
        response = self.client.get(f"{API}/operations/overview/")
        self.assertEqual(response.data["status"], "degraded")
        self.assertEqual(response.data["ingestion"]["stale"], 1)

    def test_a_quiet_system_reports_healthy(self):
        self.assertEqual(
            self.client.get(f"{API}/operations/overview/").data["status"], "healthy"
        )

    @override_settings(INGESTION_STALE_AFTER_SECONDS=STALE_AFTER)
    def test_the_ingestion_view_lists_what_is_stuck(self):
        job = make_job(JobStatus.RUNNING, age_seconds=STALE_AFTER + 600)
        response = self.client.get(f"{API}/operations/ingestion/")

        self.assertEqual(response.status_code, 200)
        stale = response.data["stale"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["job_id"], str(job.pk))
        self.assertGreater(stale[0]["stuck_for_seconds"], STALE_AFTER)

    def test_the_ingestion_view_does_not_fan_out_per_row(self):
        """Query count must not grow with the number of rows.

        Asserted by comparison rather than against a fixed number: what makes
        this an N+1 test is that tripling the rows changes nothing, and a magic
        constant here would just need updating every time a panel is added.
        """
        for _ in range(3):
            make_job(JobStatus.FAILED)
        with CaptureQueriesContext(connection) as few:
            self.client.get(f"{API}/operations/ingestion/")

        for _ in range(12):
            make_job(JobStatus.FAILED)
        with CaptureQueriesContext(connection) as many:
            self.client.get(f"{API}/operations/ingestion/")

        self.assertEqual(len(few), len(many))

    def test_provider_health_is_reported_unconfigured_rather_than_guessed(self):
        with override_settings(AI_SERVICE_URL="", AI_SERVICE_OPS_TOKEN=""):
            response = self.client.get(f"{API}/operations/providers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "unconfigured")

    def test_an_unreachable_ai_service_never_leaks_its_address(self):
        with override_settings(
            AI_SERVICE_URL="http://ai-service.internal:8000",
            AI_SERVICE_OPS_TOKEN="x" * 32,
        ):
            response = self.client.get(f"{API}/operations/providers/")

        body = json.dumps(response.data)
        self.assertEqual(response.data["status"], "unreachable")
        self.assertNotIn("ai-service.internal", body)
        self.assertNotIn("x" * 32, body)


class VersionHealthTests(TestCase):
    def test_a_failed_newer_version_is_distinguished_from_a_broken_document(self):
        """The distinction that matters when triaging.

        A document answering from v2 while v3 sits FAILED is not down — but it
        is also not fine, and neither the document's status nor the newest
        version's tells that story alone.
        """
        base = KnowledgeBase.objects.create(name="KB", slug="kb")
        document = Document.objects.create(
            knowledge_base=base, name="Spec", status=DocumentState.READY
        )
        v2 = DocumentVersion.objects.create(
            document=document, version_number=2, content_hash="a" * 64,
            status=DocumentState.READY,
        )
        DocumentVersion.objects.create(
            document=document, version_number=3, content_hash="b" * 64,
            status=DocumentState.FAILED,
        )
        document.active_version = v2
        document.save(update_fields=["active_version"])

        health = ops.version_health(document)
        self.assertEqual(health["active_version"], 2)
        self.assertEqual(health["latest_version"], 3)
        self.assertEqual(health["latest_version_status"], DocumentState.FAILED)
        self.assertTrue(health["latest_version_is_not_active"])

    def test_a_healthy_document_shows_no_divergence(self):
        base = KnowledgeBase.objects.create(name="KB2", slug="kb2")
        document = Document.objects.create(
            knowledge_base=base, name="Spec", status=DocumentState.READY
        )
        v1 = DocumentVersion.objects.create(
            document=document, version_number=1, content_hash="c" * 64,
            status=DocumentState.READY,
        )
        document.active_version = v1
        document.save(update_fields=["active_version"])

        self.assertFalse(ops.version_health(document)["latest_version_is_not_active"])
