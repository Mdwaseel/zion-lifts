"""Nothing in the control room is reachable without staff access."""

from apps.adminpanel.registry import registry

from .base import API, AdminPanelTestCase


class AccessTests(AdminPanelTestCase):
    ENDPOINTS = [
        "/dashboard/",
        "/navigation/",
        "/activity/",
        "/lifts/",
        "/lifts/schema/",
        "/enquiries/",
    ]

    def test_anonymous_is_refused_everywhere(self):
        client = self.as_anonymous()
        for path in self.ENDPOINTS:
            with self.subTest(path=path):
                self.assertEqual(client.get(f"{API}{path}").status_code, 401)

    def test_a_signed_in_non_staff_user_is_refused_everywhere(self):
        client = self.as_non_staff()
        for path in self.ENDPOINTS:
            with self.subTest(path=path):
                self.assertEqual(client.get(f"{API}{path}").status_code, 403)

    def test_a_non_staff_user_cannot_write(self):
        client = self.as_non_staff()
        res = client.post(f"{API}/milestones/", {"year": "2026", "title": "Nope"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_staff_may_read(self):
        for path in self.ENDPOINTS:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f"{API}{path}").status_code, 200)

    def test_every_registered_resource_is_routed_and_staff_only(self):
        """A resource added to the registry must not arrive unprotected."""
        anonymous = self.as_anonymous()
        for resource in registry:
            with self.subTest(resource=resource.key):
                self.assertEqual(self.client.get(f"{API}/{resource.key}/").status_code, 200)
                self.assertEqual(anonymous.get(f"{API}/{resource.key}/").status_code, 401)


class ResourceRuleTests(AdminPanelTestCase):
    def test_an_enquiry_cannot_be_created_through_the_panel(self):
        """Enquiries are records of what a customer sent, not authored content."""
        res = self.client.post(
            f"{API}/enquiries/",
            {"name": "Invented", "phone": "9000000000", "email": "x@example.com"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_an_enquiry_cannot_be_deleted_through_the_panel(self):
        enquiry = _an_enquiry()
        res = self.client.delete(f"{API}/enquiries/{enquiry.pk}/")
        self.assertEqual(res.status_code, 403)

    def test_site_settings_cannot_be_created_or_deleted(self):
        self.assertEqual(self.client.post(f"{API}/site-settings/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"{API}/site-settings/1/").status_code, 403)

    def test_an_editable_collection_still_accepts_writes(self):
        res = self.client.post(
            f"{API}/milestones/", {"year": "2026", "title": "A milestone"}, format="json"
        )
        self.assertEqual(res.status_code, 201)


def _an_enquiry():
    from apps.adminpanel.models import Enquiry

    return Enquiry.objects.create(
        name="A Visitor", phone="9000000000", email="visitor@example.com", consent=True
    )
