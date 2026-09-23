"""Shared fixtures for the control-room tests."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

User = get_user_model()

API = "/api/admin"

STAFF_EMAIL = "control@zionlifts.test"
PLAIN_EMAIL = "visitor@zionlifts.test"
PASSWORD = "an-ordinary-long-passphrase-42"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AdminPanelTestCase(TestCase):
    """A staff user, a non-staff user, and a signed-in client.

    Authentication is exercised properly in ``apps.accounts``; these tests use
    ``force_authenticate`` so a failure here always means the panel is wrong
    rather than the login is.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="control",
            email=STAFF_EMAIL,
            password=PASSWORD,
            is_staff=True,
            first_name="Control",
            last_name="Room",
        )
        cls.plain = User.objects.create_user(
            username="visitor", email=PLAIN_EMAIL, password=PASSWORD
        )

    def setUp(self):
        cache.clear()
        logging.disable(logging.CRITICAL)
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def tearDown(self):
        logging.disable(logging.NOTSET)
        cache.clear()

    def as_anonymous(self) -> APIClient:
        return APIClient()

    def as_non_staff(self) -> APIClient:
        client = APIClient()
        client.force_authenticate(self.plain)
        return client

    # --- helpers ----------------------------------------------------------
    def get(self, path, expect=200, **params):
        res = self.client.get(f"{API}{path}", params)
        self.assertEqual(res.status_code, expect, f"GET {path} -> {res.status_code} {res.content[:200]}")
        return res.json() if res.content else {}

    def post(self, path, body=None, expect=201):
        res = self.client.post(f"{API}{path}", body or {}, format="json")
        self.assertEqual(res.status_code, expect, f"POST {path} -> {res.status_code} {res.content[:200]}")
        return res.json() if res.content else {}

    def patch(self, path, body, expect=200):
        res = self.client.patch(f"{API}{path}", body, format="json")
        self.assertEqual(res.status_code, expect, f"PATCH {path} -> {res.status_code} {res.content[:200]}")
        return res.json() if res.content else {}
