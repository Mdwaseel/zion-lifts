"""DRF authentication that reads the JWT from an HttpOnly cookie.

Two things separate this from SimpleJWT's header-based class:

1. the token is read from a cookie the browser sends automatically, so no
   JavaScript ever holds it — which is the whole point of the exercise;
2. because it *is* a cookie, the browser attaches it to cross-site requests too,
   so this class enforces CSRF for unsafe methods exactly as DRF's
   ``SessionAuthentication`` does. Cookie authentication without that check is
   the classic CSRF hole.
"""

from __future__ import annotations

import logging

from django.middleware.csrf import CsrfViewMiddleware
from django.conf import settings
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

log = logging.getLogger("apps.accounts.security")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class _CSRFCheck(CsrfViewMiddleware):
    """Exposes the middleware's rejection as a raise rather than a response."""

    def _reject(self, request, reason):
        return reason


class JWTCookieAuthentication(JWTAuthentication):
    """Authenticate from the access cookie, and enforce CSRF for unsafe methods.

    The CSRF check lives in the *default* class rather than in an opt-in
    subclass on purpose. This class is on DRF's global authentication list, so
    the first state-changing endpoint anyone adds inherits it — and inheriting
    cookie authentication without a CSRF check is precisely the hole this
    module exists to close. Making the safe behaviour the default means nobody
    has to remember to opt in.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE)
        if not raw_token:
            return None

        try:
            validated = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            # Treated as "not signed in", not as an error. This class is on the
            # global default list, so raising here would turn every public GET
            # into a 401 the moment a stale cookie is present. Endpoints that
            # require a user still answer 401 via their permission class, which
            # is the signal the front end's refresh interceptor acts on.
            return None

        user = self.get_user(validated)

        # Same rule as DRF's SessionAuthentication: a credential the browser
        # attaches by itself is only safe on an unsafe method if the request
        # also proves it came from our own origin.
        if request.method not in SAFE_METHODS:
            self.enforce_csrf(request)

        return user, validated

    def enforce_csrf(self, request) -> None:
        check = _CSRFCheck(lambda req: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")
