"""Cookies, CSRF, refresh, logout, /me/ and the route through to the admin."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import services

from .base import (
    CAPTCHA_URL,
    LOGIN_URL,
    LOGOUT_URL,
    ME_URL,
    PLAIN_EMAIL,
    PLAIN_PASSWORD,
    REFRESH_URL,
    STAFF_EMAIL,
    AuthTestCase,
)


class CookieTests(AuthTestCase):
    def test_both_tokens_are_written_to_httponly_cookies(self):
        res = self.login()

        for name in (settings.JWT_ACCESS_COOKIE, settings.JWT_REFRESH_COOKIE):
            with self.subTest(cookie=name):
                cookie = res.cookies[name]
                self.assertTrue(cookie["httponly"])
                self.assertEqual(cookie["samesite"], settings.AUTH_COOKIE_SAMESITE)
                self.assertTrue(cookie.value)

    def test_the_refresh_cookie_is_scoped_to_the_accounts_endpoints(self):
        res = self.login()

        self.assertEqual(res.cookies[settings.JWT_ACCESS_COOKIE]["path"], "/")
        self.assertEqual(res.cookies[settings.JWT_REFRESH_COOKIE]["path"], "/api/accounts/")

    def test_cookie_lifetimes_match_the_token_lifetimes(self):
        res = self.login()

        self.assertEqual(
            res.cookies[settings.JWT_ACCESS_COOKIE]["max-age"],
            int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        )
        self.assertEqual(
            res.cookies[settings.JWT_REFRESH_COOKIE]["max-age"],
            int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )

    def test_the_token_value_is_never_in_the_response_body(self):
        res = self.login()
        token = res.cookies[settings.JWT_ACCESS_COOKIE].value
        self.assertNotIn(token, res.content.decode())

    @override_settings(AUTH_COOKIE_SECURE=True)
    def test_cookies_are_marked_secure_when_configured(self):
        res = self.login()
        self.assertTrue(res.cookies[settings.JWT_ACCESS_COOKIE]["secure"])
        self.assertTrue(res.cookies[settings.JWT_REFRESH_COOKIE]["secure"])

    def test_logout_clears_both_cookies(self):
        self.login()
        res = self.client.post(LOGOUT_URL, {}, format="json")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["detail"], "Logged out successfully.")
        for name in (settings.JWT_ACCESS_COOKIE, settings.JWT_REFRESH_COOKIE):
            with self.subTest(cookie=name):
                self.assertEqual(res.cookies[name].value, "")
                self.assertEqual(res.cookies[name]["max-age"], 0)

    def test_logout_ends_the_admin_session_too(self):
        self.login()
        self.client.post(LOGOUT_URL, {}, format="json")
        self.assertNotIn("_auth_user_id", self.client.session)


class MeTests(AuthTestCase):
    def test_an_authenticated_request_gets_the_user(self):
        self.login()
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            {
                "id": self.staff.pk,
                "email": STAFF_EMAIL,
                "name": "Control Room",
                "is_staff": True,
                "is_superuser": False,
            },
        )

    def test_an_unauthenticated_request_is_401(self):
        self.assertEqual(self.client.get(ME_URL).status_code, 401)

    def test_nothing_sensitive_is_returned(self):
        self.login()
        body = str(self.client.get(ME_URL).json()).lower()

        for forbidden in ("password", "token", "secret", "session"):
            with self.subTest(field=forbidden):
                self.assertNotIn(forbidden, body)

    def test_the_cookie_alone_authenticates_the_request(self):
        # No Authorization header and no session - only the JWT cookie.
        access, _ = services.create_tokens(self.staff)
        client = APIClient()
        client.cookies[settings.JWT_ACCESS_COOKIE] = access

        self.assertEqual(client.get(ME_URL).status_code, 200)

    def test_a_junk_access_cookie_reads_as_signed_out_not_as_an_error(self):
        client = APIClient()
        client.cookies[settings.JWT_ACCESS_COOKIE] = "not.a.jwt"

        self.assertEqual(client.get(ME_URL).status_code, 401)
        # ...and it must not break the public API for someone holding a stale one.
        self.assertEqual(client.get("/api/site/").status_code, 200)


class RefreshTests(AuthTestCase):
    def test_a_valid_refresh_cookie_mints_a_new_access_cookie(self):
        self.login()
        old_access = self.client.cookies[settings.JWT_ACCESS_COOKIE].value

        res = self.client.post(REFRESH_URL, {}, format="json")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"detail": "Token refreshed."})
        self.assertNotEqual(res.cookies[settings.JWT_ACCESS_COOKIE].value, old_access)

    def test_the_refresh_token_is_rotated_and_the_old_one_retired(self):
        self.login()
        first = self.client.cookies[settings.JWT_REFRESH_COOKIE].value

        self.client.post(REFRESH_URL, {}, format="json")
        second = self.client.cookies[settings.JWT_REFRESH_COOKIE].value
        self.assertNotEqual(first, second)

        # Replaying the spent token fails - this is what makes theft detectable.
        replay = APIClient()
        replay.cookies[settings.JWT_REFRESH_COOKIE] = first
        self.assertEqual(replay.post(REFRESH_URL, {}, format="json").status_code, 401)

    def test_no_refresh_cookie_is_401(self):
        res = self.client.post(REFRESH_URL, {}, format="json")

        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], "no_refresh_token")

    def test_an_expired_or_malformed_token_is_401_and_clears_the_cookies(self):
        client = APIClient()
        client.cookies[settings.JWT_REFRESH_COOKIE] = "expired.rubbish.token"

        res = client.post(REFRESH_URL, {}, format="json")

        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], "refresh_invalid")
        self.assertEqual(res.cookies[settings.JWT_ACCESS_COOKIE].value, "")

    def test_a_blacklisted_token_cannot_be_refreshed(self):
        refresh = RefreshToken.for_user(self.staff)
        refresh.blacklist()

        client = APIClient()
        client.cookies[settings.JWT_REFRESH_COOKIE] = str(refresh)
        self.assertEqual(client.post(REFRESH_URL, {}, format="json").status_code, 401)

    def test_logout_blacklists_the_refresh_token(self):
        self.login()
        stolen = self.client.cookies[settings.JWT_REFRESH_COOKIE].value
        self.client.post(LOGOUT_URL, {}, format="json")

        thief = APIClient()
        thief.cookies[settings.JWT_REFRESH_COOKIE] = stolen
        self.assertEqual(thief.post(REFRESH_URL, {}, format="json").status_code, 401)

    def test_a_deactivated_account_cannot_refresh(self):
        self.login()
        get_user_model().objects.filter(pk=self.staff.pk).update(is_active=False)

        res = self.client.post(REFRESH_URL, {}, format="json")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], "refresh_invalid")

    def test_a_deleted_account_cannot_refresh(self):
        refresh = RefreshToken.for_user(self.plain)
        get_user_model().objects.filter(pk=self.plain.pk).delete()

        client = APIClient()
        client.cookies[settings.JWT_REFRESH_COOKIE] = str(refresh)
        # 401, not a 500 from a DoesNotExist escaping the view.
        self.assertEqual(client.post(REFRESH_URL, {}, format="json").status_code, 401)

    def test_no_tokens_appear_in_the_refresh_response_body(self):
        self.login()
        res = self.client.post(REFRESH_URL, {}, format="json")
        self.assertEqual(set(res.json()), {"detail"})


class CsrfTests(AuthTestCase):
    """The endpoints are cookie-authenticated, so CSRF has to be real."""

    def setUp(self):
        super().setUp()
        self.client = APIClient(enforce_csrf_checks=True)

    def _csrf_token(self) -> str:
        self.client.get(CAPTCHA_URL)  # ensure_csrf_cookie seeds it
        return self.client.cookies["csrftoken"].value

    def _sign_in(self):
        token = self._csrf_token()
        return self.client.post(
            LOGIN_URL, self.login_payload(), format="json", HTTP_X_CSRFTOKEN=token
        )

    def test_the_captcha_endpoint_hands_out_a_csrf_cookie(self):
        res = self.client.get(CAPTCHA_URL)
        self.assertIn("csrftoken", res.cookies)

    def test_login_without_a_csrf_token_is_refused(self):
        res = self.client.post(LOGIN_URL, self.login_payload(), format="json")

        self.assertEqual(res.status_code, 403)
        self.assertNotIn(settings.JWT_ACCESS_COOKIE, res.cookies)

    def test_login_with_the_csrf_token_succeeds(self):
        self.assertEqual(self._sign_in().status_code, 200)

    def test_refresh_without_a_csrf_token_is_refused(self):
        self._sign_in()
        self.assertEqual(self.client.post(REFRESH_URL, {}, format="json").status_code, 403)

    def test_logout_without_a_csrf_token_is_refused(self):
        self._sign_in()

        res = self.client.post(LOGOUT_URL, {}, format="json")
        self.assertEqual(res.status_code, 403)
        # The session survives: a third-party page could not sign the user out.
        self.assertIn("_auth_user_id", self.client.session)

    def test_reading_the_current_user_needs_no_csrf_token(self):
        self._sign_in()
        self.assertEqual(self.client.get(ME_URL).status_code, 200)


class DefaultAuthenticationCsrfTests(AuthTestCase):
    """The globally-installed authentication class must enforce CSRF itself.

    DRF marks every APIView csrf_exempt, so CsrfViewMiddleware will not catch a
    gap here. If this ever regresses, the next staff-writable endpoint anyone
    adds inherits cookie authentication with no CSRF protection at all.
    """

    def test_the_default_class_is_the_csrf_enforcing_one(self):
        from rest_framework.settings import api_settings

        from apps.accounts.authentication import JWTCookieAuthentication

        self.assertIs(api_settings.DEFAULT_AUTHENTICATION_CLASSES[0], JWTCookieAuthentication)

    def test_an_unsafe_request_on_a_cookie_alone_is_refused_without_a_csrf_token(self):
        access, _ = services.create_tokens(self.staff)
        client = APIClient(enforce_csrf_checks=True)
        client.cookies[settings.JWT_ACCESS_COOKIE] = access

        res = client.post(LOGOUT_URL, {}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_a_safe_request_on_a_cookie_alone_still_works(self):
        access, _ = services.create_tokens(self.staff)
        client = APIClient(enforce_csrf_checks=True)
        client.cookies[settings.JWT_ACCESS_COOKIE] = access

        self.assertEqual(client.get(ME_URL).status_code, 200)


class AdminPermissionTests(AuthTestCase):
    def test_can_access_admin_matches_what_the_admin_itself_allows(self):
        from apps.accounts.permissions import can_access_admin

        self.assertTrue(can_access_admin(self.staff))
        self.assertFalse(can_access_admin(self.plain))

        self.staff.is_active = False
        self.assertFalse(can_access_admin(self.staff))

    def test_is_staff_permission_rejects_anonymous_and_non_staff(self):
        from django.contrib.auth.models import AnonymousUser

        from apps.accounts.permissions import IsStaffUser

        permission = IsStaffUser()
        request = type("R", (), {"user": AnonymousUser()})()
        self.assertFalse(permission.has_permission(request, None))

        request.user = self.plain
        self.assertFalse(permission.has_permission(request, None))

        request.user = self.staff
        self.assertTrue(permission.has_permission(request, None))


@override_settings(
    # The admin templates run {% static %}; the project's manifest storage wants a
    # collectstatic run that the test suite has no reason to perform.
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class AdminAccessTests(AuthTestCase):
    def test_a_staff_user_reaches_the_admin_after_logging_in(self):
        self.login()

        res = self.client.get("/admin/", follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("/admin/login/", res.request["PATH_INFO"])

    def test_a_non_staff_user_is_bounced_to_the_admin_login(self):
        self.login(email=PLAIN_EMAIL, password=PLAIN_PASSWORD)

        res = self.client.get("/admin/", follow=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login/", res["Location"])

    def test_signing_out_closes_the_admin_too(self):
        self.login()
        self.client.post(LOGOUT_URL, {}, format="json")

        res = self.client.get("/admin/", follow=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login/", res["Location"])

    def test_logging_in_cycles_the_session_key(self):
        # Session fixation: whatever id the visitor arrived with is discarded.
        self.client.get(CAPTCHA_URL)
        session = self.client.session
        session["planted"] = "value"
        session.save()
        before = session.session_key

        self.login()
        after = self.client.cookies["sessionid"].value

        self.assertTrue(after)
        self.assertNotEqual(before, after)


class ExistingApiTests(AuthTestCase):
    """The public API must behave exactly as it did before authentication existed."""

    # Stats, certifications, FAQ categories and service pillars used to be on
    # this list. They are static content in the front end now and have no
    # endpoint at all — see adminpanel migration 0004.
    PUBLIC = [
        "/api/site/",
        "/api/offices/",
        "/api/partners/",
        "/api/lifts/",
        "/api/projects/",
        "/api/journal/",
        "/api/testimonials/",
        "/api/gallery/",
        "/api/team/",
        "/api/awards/",
    ]

    def test_public_endpoints_are_still_open_to_anonymous_callers(self):
        for path in self.PUBLIC:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_public_endpoints_still_work_while_signed_in(self):
        self.login()
        for path in self.PUBLIC:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_the_enquiry_endpoint_still_accepts_an_anonymous_post(self):
        res = self.client.post(
            "/api/enquiries/",
            {
                "name": "A Visitor",
                "phone": "9000000000",
                "email": "visitor@example.com",
                "message": "Please quote for a home lift.",
                "consent": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
