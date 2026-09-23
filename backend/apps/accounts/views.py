"""The five authentication endpoints.

Each view does routing, status codes and logging; the actual work — issuing
tokens, writing cookies, checking a CAPTCHA — lives in ``services`` and
``captcha`` so it can be tested and reused without a request.

A note on CSRF, because it is the easy thing to get wrong here. DRF exempts its
own views from ``CsrfViewMiddleware`` and expects the authentication class to
run the check instead. That works for /me/ and /logout/, which have a user to
authenticate. /login/ and /refresh/ have no user yet, so they are wrapped in
``csrf_protect`` explicitly. Nothing in this module is ``csrf_exempt``.
"""

from __future__ import annotations

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from . import captcha as captcha_service
from . import services
from .authentication import JWTCookieAuthentication
from .permissions import can_access_admin
from .serializers import LoginSerializer, UserSerializer
from .throttling import CaptchaThrottle, LoginAccountThrottle, LoginIPThrottle

log = logging.getLogger("apps.accounts.security")

INVALID_CREDENTIALS = "Invalid email or password."
INVALID_CAPTCHA = "Invalid or expired CAPTCHA."


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CaptchaView(APIView):
    """GET a fresh challenge.

    Doubles as the front end's way of obtaining a CSRF token: this is the first
    call the login page makes, and ``ensure_csrf_cookie`` means the response
    carries the ``csrftoken`` cookie the subsequent POST has to echo back.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [CaptchaThrottle]

    def get(self, request):
        challenge = captcha_service.issue_challenge()
        return Response({"captcha_id": challenge.captcha_id, "image": challenge.image})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """Email + password + CAPTCHA in; two HttpOnly cookies out.

    The response body never contains a token. That is the entire reason for the
    cookie design: a value JavaScript cannot read is a value an injected script
    cannot exfiltrate.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle, LoginAccountThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400, field-level
        data = serializer.validated_data
        ip = services.client_ip(request)

        # CAPTCHA first: it is cheap, and it means a scripted credential-stuffing
        # run never reaches the password hasher.
        if not captcha_service.verify_challenge(data["captcha_id"], data["captcha_answer"]):
            log.warning("Login rejected (captcha) from %s", ip)
            return Response(
                {"detail": INVALID_CAPTCHA, "code": "captcha_invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = services.authenticate_user(request, data["email"], data["password"])
        if user is None:
            self._record_account_failure(request)
            # The log records the address; the response does not distinguish
            # "no such account" from "wrong password".
            log.warning("Login failed for %s from %s", data["email"], ip)
            return Response(
                {"detail": INVALID_CREDENTIALS, "code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access, refresh = services.create_tokens(user)

        # Staff only: the admin is server-rendered off the session cookie, so a
        # session is established here rather than after a second round trip.
        # Non-staff are authenticated for the API but get no admin session, and
        # the front end sends them to an unauthorised screen on ``is_staff``.
        if can_access_admin(user):
            services.start_admin_session(request, user)

        payload = UserSerializer(user).data
        response = Response({"detail": "Login successful.", "user": payload})
        services.set_auth_cookies(response, access, refresh)

        log.info(
            "Login succeeded for user %s (staff=%s) from %s", user.pk, user.is_staff, ip
        )
        return response

    def _record_account_failure(self, request) -> None:
        for throttle in self.get_throttles():
            if isinstance(throttle, LoginAccountThrottle):
                throttle.record_failure(request, self)


@method_decorator(csrf_protect, name="dispatch")
class RefreshView(APIView):
    """Exchange the refresh cookie for a new access cookie.

    The client sends nothing: the browser attaches the refresh cookie because
    this path is inside its scope, and the new tokens go straight back into
    cookies. Nothing about either token passes through JavaScript.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle]

    def post(self, request):
        token = services.read_refresh_cookie(request)
        if not token:
            return Response(
                {"detail": "Authentication credentials were not provided.", "code": "no_refresh_token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            access, new_refresh = services.rotate_tokens(token)
        except TokenError:
            log.warning("Refresh rejected from %s", services.client_ip(request))
            # Clear the cookies as well: a refresh token that will not validate
            # again is only going to trigger the same failure on every request.
            response = Response(
                {"detail": "Session expired. Please sign in again.", "code": "refresh_invalid"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            services.clear_auth_cookies(response)
            return response

        response = Response({"detail": "Token refreshed."})
        services.set_auth_cookies(response, access, new_refresh)
        return response


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    """Revoke the refresh token, drop both cookies, end the admin session.

    Deliberately open to unauthenticated callers: if the access token has
    already expired the visitor still has cookies in their browser, and refusing
    to clear them would be unhelpful. CSRF still applies, so another site cannot
    sign a visitor out.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        services.blacklist_refresh_token(services.read_refresh_cookie(request))
        services.end_admin_session(request)

        response = Response({"detail": "Logged out successfully."})
        services.clear_auth_cookies(response)

        log.info("Logout from %s", services.client_ip(request))
        return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    """Who is signed in. The front end's session check on first paint.

    Uses the project default — the JWT cookie first, then the Django session —
    rather than pinning JWT only. Every other authenticated endpoint accepts
    both, and a staff user already signed into /admin/ should not be told they
    are anonymous when they open the control room.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
