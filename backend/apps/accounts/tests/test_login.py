"""The login endpoint: credentials, CAPTCHA, cookies, rate limits, staff."""

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.accounts.throttling import LoginAccountThrottle, LoginIPThrottle

from .base import (
    LOGIN_URL,
    PLAIN_EMAIL,
    PLAIN_PASSWORD,
    STAFF_EMAIL,
    STAFF_PASSWORD,
    AuthTestCase,
    throttle_rate,
)

User = get_user_model()


class LoginSuccessTests(AuthTestCase):
    def test_valid_credentials_sign_a_staff_user_in(self):
        res = self.login()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["detail"], "Login successful.")

    def test_the_response_carries_the_user_but_no_tokens(self):
        body = self.login().json()

        self.assertEqual(body["user"]["email"], STAFF_EMAIL)
        self.assertTrue(body["user"]["is_staff"])
        self.assertNotIn("password", body["user"])

        serialised = str(body)
        for leak in ("access", "refresh", "token", "eyJ"):
            self.assertNotIn(leak, serialised.lower() if leak != "eyJ" else serialised)

    def test_email_matching_ignores_case_and_whitespace(self):
        res = self.login(email=f"  {STAFF_EMAIL.upper()}  ")
        self.assertEqual(res.status_code, 200)

    def test_a_non_staff_user_authenticates_but_is_flagged(self):
        res = self.login(email=PLAIN_EMAIL, password=PLAIN_PASSWORD)

        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["user"]["is_staff"])
        # No admin session: the control room stays shut.
        self.assertNotIn("sessionid", res.cookies)

    def test_a_staff_login_also_opens_a_django_admin_session(self):
        res = self.login()
        self.assertIn("sessionid", res.cookies)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.staff.pk)

    def test_an_inactive_account_cannot_sign_in(self):
        User.objects.filter(pk=self.plain.pk).update(is_active=False)
        res = self.login(email=PLAIN_EMAIL, password=PLAIN_PASSWORD)
        self.assertEqual(res.status_code, 401)


class LoginFailureTests(AuthTestCase):
    def test_a_wrong_password_is_rejected_generically(self):
        res = self.login(password="not-the-password")

        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Invalid email or password.")

    def test_an_unknown_address_gives_the_same_answer_as_a_wrong_password(self):
        unknown = self.login(email="nobody@zionlifts.test", password="whatever-at-all")
        wrong = self.login(password="not-the-password")

        self.assertEqual(unknown.status_code, wrong.status_code)
        self.assertEqual(unknown.json()["detail"], wrong.json()["detail"])

    def test_no_cookies_are_issued_on_failure(self):
        res = self.login(password="not-the-password")
        self.assertNotIn(settings.JWT_ACCESS_COOKIE, res.cookies)
        self.assertNotIn(settings.JWT_REFRESH_COOKIE, res.cookies)

    def test_a_wrong_captcha_is_rejected_before_the_password_is_checked(self):
        payload = self.login_payload(password="not-the-password")
        payload["captcha_answer"] = "ZZZZZ"

        res = self.client.post(LOGIN_URL, payload, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["detail"], "Invalid or expired CAPTCHA.")

    def test_a_captcha_cannot_be_used_for_two_logins(self):
        payload = self.login_payload()
        self.assertEqual(self.client.post(LOGIN_URL, payload, format="json").status_code, 200)

        again = self.client.post(LOGIN_URL, payload, format="json")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["code"], "captcha_invalid")

    def test_missing_fields_are_a_400_with_field_errors(self):
        for field in ("email", "password", "captcha_id", "captcha_answer"):
            with self.subTest(field=field):
                payload = self.login_payload()
                payload.pop(field)
                res = self.client.post(LOGIN_URL, payload, format="json")

                self.assertEqual(res.status_code, 400)
                self.assertIn(field, res.json())

    def test_a_malformed_email_is_a_400(self):
        payload = self.login_payload()
        payload["email"] = "not-an-address"
        self.assertEqual(self.client.post(LOGIN_URL, payload, format="json").status_code, 400)

    def test_duplicate_addresses_are_refused_rather_than_guessed(self):
        # auth.User does not enforce a unique email, so this is reachable.
        User.objects.create_user(
            username="second", email=STAFF_EMAIL.upper(), password=STAFF_PASSWORD
        )
        self.assertEqual(self.login().status_code, 401)


class LoginRateLimitTests(AuthTestCase):
    def test_repeated_attempts_from_one_address_are_throttled(self):
        with throttle_rate(LoginIPThrottle, "3/minute"):
            statuses = [
                self.client.post(
                    LOGIN_URL, self.login_payload(password="wrong-one"), format="json"
                ).status_code
                for _ in range(5)
            ]
        self.assertEqual(statuses[-1], 429)

    def test_the_throttle_response_says_when_to_retry(self):
        with throttle_rate(LoginIPThrottle, "1/minute"):
            self.client.post(LOGIN_URL, self.login_payload(), format="json")
            res = self.client.post(LOGIN_URL, self.login_payload(), format="json")

        self.assertEqual(res.status_code, 429)
        self.assertIn("Retry-After", res.headers)

    def test_failures_against_one_account_are_capped_independently_of_the_ip(self):
        with throttle_rate(LoginAccountThrottle, "3/hour"):
            for _ in range(3):
                self.client.post(
                    LOGIN_URL, self.login_payload(password="wrong-one"), format="json"
                )
            res = self.client.post(LOGIN_URL, self.login_payload(), format="json")

        self.assertEqual(res.status_code, 429)

    def test_a_spoofed_forwarded_for_header_does_not_win_a_fresh_bucket(self):
        """The bypass this exists to stop.

        With NUM_PROXIES unset, DRF keys the throttle on the whole X-Forwarded-For
        header, so varying it puts every request in a new bucket and the limit
        never binds. NUM_PROXIES=0 makes it ignore the header entirely.
        """
        with throttle_rate(LoginIPThrottle, "3/minute"):
            statuses = [
                self.client.post(
                    LOGIN_URL,
                    self.login_payload(password="wrong-one"),
                    format="json",
                    HTTP_X_FORWARDED_FOR=f"10.0.0.{n}",
                ).status_code
                for n in range(6)
            ]
        self.assertIn(429, statuses)

    def test_a_non_string_email_is_a_400_not_a_500(self):
        """request.data is client-controlled; the throttle must not choke on it."""
        for value in (5, ["a@b.com"], {"x": 1}, None):
            with self.subTest(value=value):
                payload = self.login_payload()
                payload["email"] = value
                res = self.client.post(LOGIN_URL, payload, format="json")
                self.assertEqual(res.status_code, 400)

    def test_failures_are_counted_even_when_they_arrive_together(self):
        """A get/modify/set counter would lose all but one of these."""
        with throttle_rate(LoginAccountThrottle, "20/hour"):
            for _ in range(5):
                self.client.post(
                    LOGIN_URL, self.login_payload(password="wrong-one"), format="json"
                )

            throttle = LoginAccountThrottle()
            request = self.client.request().wsgi_request
            request.data = {"email": STAFF_EMAIL}
            self.assertEqual(throttle.cache.get(throttle.get_cache_key(request, None)), 5)

    def test_successful_logins_do_not_fill_the_account_bucket(self):
        with throttle_rate(LoginAccountThrottle, "3/hour"):
            statuses = [
                self.client.post(LOGIN_URL, self.login_payload(), format="json").status_code
                for _ in range(5)
            ]
        self.assertEqual(statuses, [200] * 5)
