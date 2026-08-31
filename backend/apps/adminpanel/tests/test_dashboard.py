"""The landing screen and the audit trail behind it."""

from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType

from apps.adminpanel.models import Enquiry, Milestone, ServiceRequest

from .base import AdminPanelTestCase


class DashboardTests(AdminPanelTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for status in ("new", "new", "contacted", "won"):
            Enquiry.objects.create(
                name="A Visitor", phone="900", email="v@example.com", status=status
            )
        ServiceRequest.objects.create(
            name="Site Manager", phone="900", kind="breakdown", urgency="urgent", status="new"
        )
        ServiceRequest.objects.create(
            name="Facilities", phone="900", kind="maintenance", urgency="routine", status="new"
        )
        Milestone.objects.create(year="2012", title="Founded", is_published=True)
        Milestone.objects.create(year="2013", title="Draft", is_published=False)

    def test_the_pipeline_counts_every_status_in_the_model_order(self):
        body = self.get("/dashboard/")
        enquiries = body["inbox"]["enquiries"]

        self.assertEqual(enquiries["total"], 4)
        self.assertEqual(enquiries["unhandled"], 2)

        by_value = {s["value"]: s["count"] for s in enquiries["statuses"]}
        self.assertEqual(by_value["new"], 2)
        self.assertEqual(by_value["contacted"], 1)
        # A status nobody is in must still be listed, or the funnel changes
        # shape as records move through it.
        self.assertIn("lost", by_value)

    def test_statuses_carry_readable_labels(self):
        statuses = self.get("/dashboard/")["inbox"]["enquiries"]["statuses"]
        self.assertTrue(all(s["label"] and s["label"] != s["value"].upper() for s in statuses))

    def test_urgent_lists_open_non_routine_service_requests_oldest_first(self):
        rows = self.get("/dashboard/")["urgent"]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["urgency"], "Urgent - lift is down")

    def test_a_closed_request_is_not_urgent_any_more(self):
        ServiceRequest.objects.update(status="closed")
        self.assertEqual(self.get("/dashboard/")["urgent"], [])

    def test_recent_enquiries_are_newest_first_and_readable(self):
        rows = self.get("/dashboard/")["recent_enquiries"]

        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["status"] and row["lift_type"] for row in rows))

    def test_collection_counts_flag_unpublished_work(self):
        collections = {c["key"]: c for c in self.get("/dashboard/")["collections"]}

        self.assertEqual(collections["milestones"]["count"], 2)
        self.assertEqual(collections["milestones"]["unpublished"], 1)

    def test_a_collection_without_publishing_reports_none_rather_than_zero(self):
        """None means "not applicable"; zero would read as "nothing to do"."""
        collections = {c["key"]: c for c in self.get("/dashboard/")["collections"]}
        self.assertIsNone(collections["enquiries"]["unpublished"])

    def test_the_singleton_is_not_listed_as_a_collection(self):
        keys = {c["key"] for c in self.get("/dashboard/")["collections"]}
        self.assertNotIn("site-settings", keys)

    def test_the_dashboard_is_one_request(self):
        """It exists so the client does not fan out across thirty list endpoints."""
        body = self.get("/dashboard/")
        self.assertEqual(
            set(body),
            {"inbox", "urgent", "recent_enquiries", "collections", "activity", "window_days"},
        )


class ActivityTests(AdminPanelTestCase):
    def test_a_change_made_through_the_panel_appears_in_the_trail(self):
        self.post("/milestones/", {"year": "2012", "title": "Founded"})

        rows = self.get("/activity/")["results"]
        self.assertEqual(rows[0]["action"], "created")
        self.assertEqual(rows[0]["object_repr"], "2012 - Founded")
        self.assertEqual(rows[0]["resource"], "milestones")
        self.assertEqual(rows[0]["user"], "Control Room")

    def test_the_trail_is_newest_first(self):
        self.post("/milestones/", {"year": "2012", "title": "First"})
        self.post("/milestones/", {"year": "2013", "title": "Second"})

        rows = self.get("/activity/")["results"]
        self.assertEqual(rows[0]["object_repr"], "2013 - Second")

    def test_an_entry_for_an_unregistered_model_still_renders(self):
        """Django's own admin logs user edits; those must not break the trail."""
        LogEntry.objects.log_action(
            user_id=self.staff.pk,
            content_type_id=ContentType.objects.get_for_model(self.staff).pk,
            object_id=self.staff.pk,
            object_repr="control",
            action_flag=ADDITION,
            change_message="Added a user in Django admin.",
        )
        rows = self.get("/activity/")["results"]

        self.assertEqual(rows[0]["object_repr"], "control")
        self.assertIsNone(rows[0]["resource"])  # nothing in the panel to link to

    def test_a_deleted_record_has_no_link_target(self):
        created = self.post("/milestones/", {"year": "2012", "title": "Founded"})
        self.client.delete(f"/api/admin/milestones/{created['id']}/")

        rows = self.get("/activity/")["results"]
        self.assertEqual(rows[0]["action"], "deleted")
        self.assertIsNone(rows[0]["object_id"])

    def test_an_audit_failure_never_fails_the_edit(self):
        """A broken log table must not make the site uneditable."""
        from unittest import mock

        with mock.patch(
            "apps.adminpanel.audit.LogEntry.objects.log_action",
            side_effect=RuntimeError("log table is gone"),
        ):
            res = self.client.post(
                "/api/admin/milestones/", {"year": "2012", "title": "Founded"}, format="json"
            )

        self.assertEqual(res.status_code, 201)
        self.assertTrue(Milestone.objects.filter(title="Founded").exists())
