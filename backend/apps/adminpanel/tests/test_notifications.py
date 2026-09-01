"""Unread counts: what the sidebar badges say, and when they clear.

The badge answers one question — how much has arrived that nobody has picked up
— and it answers it from the record's own ``status``. There is no second
"read" flag, so these tests are mostly about that decision holding: the count
moves when the work moves, and only the two collections that fill up on their
own have one at all.
"""

from __future__ import annotations

from apps.adminpanel import notifications
from apps.adminpanel.models import Enquiry, ServiceRequest
from apps.adminpanel.registry import registry

from .base import API, AdminPanelTestCase


def enquiry(**kwargs) -> Enquiry:
    return Enquiry.objects.create(
        name="A Visitor", phone="9000000000", email="visitor@example.com", **kwargs
    )


def service_request(**kwargs) -> ServiceRequest:
    return ServiceRequest.objects.create(
        name="Site Manager", phone="9000000000", kind="breakdown", **kwargs
    )


class CountTests(AdminPanelTestCase):
    def test_nothing_waiting_is_zero_not_absent(self):
        """A collection with a badge always reports, so the UI can hide it."""
        body = self.get("/notifications/")

        self.assertEqual(body["counts"]["enquiries"], 0)
        self.assertEqual(body["counts"]["service-requests"], 0)
        self.assertEqual(body["total"], 0)

    def test_new_records_are_counted(self):
        enquiry(status="new")
        enquiry(status="new")
        service_request(status="new")

        body = self.get("/notifications/")
        self.assertEqual(body["counts"]["enquiries"], 2)
        self.assertEqual(body["counts"]["service-requests"], 1)
        self.assertEqual(body["total"], 3)

    def test_anything_already_picked_up_is_not_counted(self):
        enquiry(status="new")
        for status in ("contacted", "quoted", "won", "lost", "spam"):
            enquiry(status=status)

        self.assertEqual(self.get("/notifications/")["counts"]["enquiries"], 1)

    def test_the_badge_clears_when_the_status_moves_off_new(self):
        """Which is the moment somebody actually did something about it."""
        record = enquiry(status="new")
        self.assertEqual(self.get("/notifications/")["counts"]["enquiries"], 1)

        self.patch(f"/enquiries/{record.pk}/", {"status": "contacted"})

        self.assertEqual(self.get("/notifications/")["counts"]["enquiries"], 0)

    def test_the_total_is_the_sum_of_the_parts(self):
        enquiry(status="new")
        service_request(status="new")
        service_request(status="new")

        body = self.get("/notifications/")
        self.assertEqual(body["total"], sum(body["counts"].values()))


class WhichCollectionsAreWatchedTests(AdminPanelTestCase):
    def test_only_the_collections_that_fill_up_on_their_own(self):
        """A count on anything else would be staff's own work read back to them."""
        self.assertEqual(
            {resource.key for resource in notifications.watched()},
            {"enquiries", "service-requests"},
        )

    def test_a_watched_collection_declares_what_unread_means(self):
        for key in ("enquiries", "service-requests"):
            with self.subTest(resource=key):
                self.assertEqual(registry[key].unread_status, "new")

    def test_everything_else_declares_nothing(self):
        for resource in registry:
            if resource.key in {"enquiries", "service-requests"}:
                continue
            with self.subTest(resource=resource.key):
                self.assertEqual(resource.unread_status, "")

    def test_the_declared_status_is_a_real_choice_on_the_model(self):
        """A typo here would be a badge that silently counts nothing forever."""
        for resource in notifications.watched():
            with self.subTest(resource=resource.key):
                choices = dict(resource.model._meta.get_field("status").choices)
                self.assertIn(resource.unread_status, choices)


class DeliveryTests(AdminPanelTestCase):
    def test_the_first_paint_already_has_the_counts(self):
        """Carried on navigation so the badges do not appear a poll later."""
        enquiry(status="new")
        body = self.get("/navigation/")

        self.assertEqual(body["notifications"]["counts"]["enquiries"], 1)

    def test_navigation_and_the_poll_cannot_disagree(self):
        enquiry(status="new")
        service_request(status="new")

        self.assertEqual(
            self.get("/navigation/")["notifications"], self.get("/notifications/")
        )

    def test_the_schema_says_which_collections_have_a_badge(self):
        self.assertEqual(self.get("/enquiries/schema/")["unread_status"], "new")
        self.assertEqual(self.get("/projects/schema/")["unread_status"], "")


class PermissionTests(AdminPanelTestCase):
    def test_an_anonymous_caller_cannot_read_the_counts(self):
        """How much work is waiting is not public."""
        self.assertEqual(self.as_anonymous().get(f"{API}/notifications/").status_code, 401)

    def test_a_signed_in_non_staff_user_cannot_read_the_counts(self):
        self.assertEqual(self.as_non_staff().get(f"{API}/notifications/").status_code, 403)
