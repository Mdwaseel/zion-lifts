"""Shared fixtures for the authentication tests."""

from __future__ import annotations

import logging
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts import captcha as captcha_service

User = get_user_model()

STAFF_EMAIL = "control@zionlifts.test"
STAFF_PASSWORD = "an-ordinary-long-passphrase-42"
PLAIN_EMAIL = "visitor@zionlifts.test"
PLAIN_PASSWORD = "another-ordinary-passphrase-42"

CAPTCHA_URL = "/api/accounts/captcha/"
LOGIN_URL = "/api/accounts/login/"
REFRESH_URL = "/api/accounts/refresh/"
LOGOUT_URL = "/api/accounts/logout/"
ME_URL = "/api/accounts/me/"


# The suite makes a lot of login attempts; PBKDF2 at its real work factor
# turns that into a minute of waiting for nothing the tests are checking.
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthTestCase(TestCase):
    """A staff user, a non-staff user, and a way to solve a CAPTCHA.

    The tests never see the CAPTCHA answer through the API — that is the point
    of the design — so ``solve`` reaches into the store the way only a test can:
    it issues the challenge itself and keeps the plaintext.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="control",
            email=STAFF_EMAIL,
            password=STAFF_PASSWORD,
            is_staff=True,
            first_name="Control",
            last_name="Room",
        )
        cls.plain = User.objects.create_user(
            username="visitor", email=PLAIN_EMAIL, password=PLAIN_PASSWORD
        )

    def setUp(self):
        cache.clear()  # throttle buckets and captcha entries are per-test
        self.client = APIClient(enforce_csrf_checks=False)
        # The security log is asserted on where it matters; elsewhere it is noise.
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)
        cache.clear()

    # --- captcha helpers ---------------------------------------------------
    def issue_captcha(self) -> tuple[str, str]:
        """Return (captcha_id, plaintext answer) by driving the module directly."""
        answers = {}
        original = captcha_service._digest

        def spy(answer: str) -> str:
            answers.setdefault("value", answer)
            return original(answer)

        captcha_service._digest = spy
        try:
            challenge = captcha_service.issue_challenge()
        finally:
            captcha_service._digest = original
        return challenge.captcha_id, answers["value"]

    def login_payload(self, email=STAFF_EMAIL, password=STAFF_PASSWORD, **overrides):
        captcha_id, answer = self.issue_captcha()
        payload = {
            "email": email,
            "password": password,
            "captcha_id": captcha_id,
            "captcha_answer": answer,
        }
        payload.update(overrides)
        return payload

    def login(self, **overrides):
        return self.client.post(LOGIN_URL, self.login_payload(**overrides), format="json")


@contextmanager
def throttle_rate(throttle_cls, rate: str):
    """Temporarily change one throttle's rate.

    ``override_settings(REST_FRAMEWORK=...)`` does not reach throttles: DRF
    binds ``SimpleRateThrottle.THROTTLE_RATES`` to the settings dict once, at
    import, so the class has to be patched instead.
    """
    original = throttle_cls.THROTTLE_RATES
    throttle_cls.THROTTLE_RATES = {**original, throttle_cls.scope: rate}
    try:
        yield
    finally:
        throttle_cls.THROTTLE_RATES = original
