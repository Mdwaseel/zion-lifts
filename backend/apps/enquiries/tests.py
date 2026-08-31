"""Contract tests for the two forms that carry every lead on the site."""

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.catalog.models import LiftType

from .models import Enquiry, ServiceRequest

VALID = {
    "property_type": "villa",
    "project_stage": "construction",
    "location": "Jubilee Hills, Hyderabad",
    "floors": "Ground + 3",
    "capacity": "6 persons / 408 kg",
    "stops": "4",
    "installation_kind": "new",
    "name": "Test Person",
    "phone": "+91 90000 00000",
    "email": "person@example.com",
    "consent": True,
}


class EnquiryApiTests(TestCase):
    def setUp(self):
        # the enquiry throttle is scoped per-IP and its history lives in the
        # cache, so it would carry over between tests in the same run
        cache.clear()
        self.client = APIClient()
        self.url = "/api/enquiries/"

    def test_creates_enquiry_and_returns_reference(self):
        res = self.client.post(self.url, VALID, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertIn("reference", res.data)
        self.assertTrue(res.data["reference"].startswith("ZL-"))

        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.name, "Test Person")
        self.assertEqual(enquiry.location, "Jubilee Hills, Hyderabad")
        self.assertEqual(enquiry.status, "new")

    def test_links_a_lift_type_when_one_is_chosen(self):
        lift = LiftType.objects.create(
            slug="home-elevator", name="Home Elevator", tagline="t", summary="s"
        )
        res = self.client.post(self.url, {**VALID, "lift_type": lift.pk}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Enquiry.objects.get().lift_type, lift)

    def test_carries_the_cabin_configuration_through(self):
        config = {"material": "antique-brass", "floor": "marble"}
        res = self.client.post(self.url, {**VALID, "configuration": config}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Enquiry.objects.get().configuration, config)

    def test_rejects_a_submission_without_consent(self):
        res = self.client.post(self.url, {**VALID, "consent": False}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("consent", res.data)
        self.assertFalse(Enquiry.objects.exists())

    def test_requires_a_way_to_reply(self):
        for field in ("name", "phone", "email"):
            with self.subTest(field=field):
                res = self.client.post(self.url, {**VALID, field: ""}, format="json")
                self.assertEqual(res.status_code, 400)
                self.assertIn(field, res.data)
        self.assertFalse(Enquiry.objects.exists())

    def test_rejects_a_malformed_email(self):
        res = self.client.post(self.url, {**VALID, "email": "not-an-address"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

    def test_silently_rejects_anything_that_fills_the_honeypot(self):
        res = self.client.post(self.url, {**VALID, "website": "http://spam"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Enquiry.objects.exists())

    def test_accepts_drawing_uploads(self):
        pdf = SimpleUploadedFile("plan.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        res = self.client.post(self.url, {**VALID, "uploads": [pdf]}, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.attachments.count(), 1)
        self.assertEqual(enquiry.attachments.get().original_name, "plan.pdf")

    def test_refuses_an_unsupported_attachment_type(self):
        exe = SimpleUploadedFile("payload.exe", b"MZ", content_type="application/octet-stream")
        res = self.client.post(self.url, {**VALID, "uploads": [exe]}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Enquiry.objects.exists())

    def test_refuses_more_than_six_attachments(self):
        files = [
            SimpleUploadedFile(f"p{i}.pdf", b"%PDF", content_type="application/pdf")
            for i in range(7)
        ]
        res = self.client.post(self.url, {**VALID, "uploads": files}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Enquiry.objects.exists())

    def test_a_mail_failure_does_not_lose_the_lead(self):
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
            EMAIL_HOST="127.0.0.1",
            EMAIL_PORT=1,  # nothing is listening
        ):
            res = self.client.post(self.url, VALID, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Enquiry.objects.count(), 1)


class ServiceRequestApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.url = "/api/service-requests/"
        self.payload = {
            "kind": "breakdown",
            "urgency": "urgent",
            "name": "Building Manager",
            "phone": "+91 90000 00001",
            "site_name": "Owaisi Hospitals",
            "location": "Santosh Nagar",
            "message": "Doors reopening on the third floor.",
            "consent": True,
        }

    def test_creates_a_service_request(self):
        res = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["reference"].startswith("SR-"))
        sr = ServiceRequest.objects.get()
        self.assertEqual(sr.kind, "breakdown")
        self.assertEqual(sr.urgency, "urgent")
        self.assertEqual(sr.status, "new")

    def test_email_is_optional_but_phone_is_not(self):
        res = self.client.post(self.url, {**self.payload, "email": ""}, format="json")
        self.assertEqual(res.status_code, 201, res.data)

        res = self.client.post(self.url, {**self.payload, "phone": ""}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("phone", res.data)

    def test_requires_consent(self):
        res = self.client.post(self.url, {**self.payload, "consent": False}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(ServiceRequest.objects.exists())

    def test_honeypot(self):
        res = self.client.post(self.url, {**self.payload, "website": "x"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(ServiceRequest.objects.exists())
