"""The moving parts of a login, kept out of the views.

Everything here is a small function with one job, so the five views stay short
and the cookie rules are written down exactly once.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

log = logging.getLogger("apps.accounts.security")


# --- credentials -----------------------------------------------------------
def authenticate_user(request: HttpRequest, email: str, password: str):
    """Delegate to Django's auth stack. Returns the user, or None."""
    return authenticate(request, username=email, password=password)


# --- tokens ----------------------------------------------------------------
def create_tokens(user: AbstractBaseUser) -> tuple[str, str]:
    """Mint an access/refresh pair for a user.

    The access token is deliberately short-lived (15 minutes by default): it is
    sent on every API call, is not checked against any server-side list, and so
    stays valid until it expires even if the account is disabled a minute later.
    Its blast radius is bounded by that window alone.

    The refresh token is long-lived (7 days) because it exists only to avoid
    asking for the password again. It travels to one path, is rotated on use and
    — unlike the access token — *can* be revoked, because used and logged-out
    refresh tokens go on the blacklist.
    """
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def rotate_tokens(refresh_token: str) -> tuple[str, str | None]:
    """Validate a refresh token and return (access, new refresh or None).

    Raises ``TokenError`` if the token is expired, malformed, blacklisted, or no
    longer belongs to an account that may sign in.
    """
    refresh = RefreshToken(refresh_token)

    # A refresh token stays valid for a week, so the account behind it is
    # re-checked on every use. Without this, disabling or deleting a user would
    # leave them able to mint fresh access tokens until their refresh expired.
    user = _user_for(refresh)

    access = str(refresh.access_token)

    if not settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
        return access, None

    if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION"):
        # Retire the presented token, so replaying a stolen one fails.
        #
        # This is single-token revocation, not token-family reuse detection:
        # validation and blacklisting are two steps, so a thief refreshing at
        # the same moment as the victim can still fork a second valid chain, and
        # nothing here notices that a spent token was replayed. Closing that
        # needs a family id carried in the token and revoked on reuse. Logging
        # out revokes the presented chain, which is the practical remedy today.
        try:
            refresh.blacklist()
        except AttributeError:  # blacklist app not installed
            pass

    new_refresh = RefreshToken.for_user(user)
    return str(new_refresh.access_token), str(new_refresh)


def blacklist_refresh_token(refresh_token: str | None) -> None:
    """Best-effort revocation. A logout must succeed even if this cannot."""
    if not refresh_token:
        return
    try:
        RefreshToken(refresh_token).blacklist()
    except (TokenError, AttributeError):
        log.info("Logout presented a refresh token that could not be blacklisted")


def _user_for(refresh: RefreshToken):
    """The account a refresh token belongs to, if it may still sign in.

    Raises ``TokenError`` — not DoesNotExist — for a deleted or disabled user,
    so the view answers 401 and clears the cookies rather than returning a 500.
    """
    from django.contrib.auth import get_user_model

    claim = settings.SIMPLE_JWT["USER_ID_CLAIM"]
    field = settings.SIMPLE_JWT["USER_ID_FIELD"]

    user = get_user_model().objects.filter(**{field: refresh.get(claim)}).first()
    if user is None:
        raise TokenError("No account for this token.")
    if not user.is_active:
        raise TokenError("Account is inactive.")
    return user


# --- cookies ---------------------------------------------------------------
def _cookie_kwargs(path: str) -> dict[str, Any]:
    """One place where every auth cookie's security flags are decided."""
    return {
        "httponly": True,  # never readable from JavaScript, so XSS cannot lift it
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "domain": settings.AUTH_COOKIE_DOMAIN or None,
        "path": path,
    }


def set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None) -> None:
    """Write the tokens to their cookies. The only place tokens reach a client."""
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE,
        access_token,
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        **_cookie_kwargs(settings.AUTH_COOKIE_PATH),
    )
    if refresh_token is not None:
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE,
            refresh_token,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            # Scoped to the accounts endpoints: the refresh token is not needed
            # by any other request, so it is not sent with any other request.
            **_cookie_kwargs(settings.AUTH_REFRESH_COOKIE_PATH),
        )


def clear_auth_cookies(response: Response) -> None:
    """Delete both cookies.

    Path, domain and the security flags all have to match what set them, or the
    browser treats the deletion as a different cookie and keeps the original.
    ``secure`` matters most: a browser rejects any ``SameSite=None`` cookie that
    is not also ``Secure``, so without it a cross-site deployment would return
    "Logged out successfully" while leaving a live access token in place.
    """
    for name, path in (
        (settings.JWT_ACCESS_COOKIE, settings.AUTH_COOKIE_PATH),
        (settings.JWT_REFRESH_COOKIE, settings.AUTH_REFRESH_COOKIE_PATH),
    ):
        response.delete_cookie(
            name,
            path=path,
            domain=settings.AUTH_COOKIE_DOMAIN or None,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        # delete_cookie only sets Secure for __Secure-/__Host- prefixed names,
        # so it has to be put back by hand.
        if settings.AUTH_COOKIE_SECURE:
            response.cookies[name]["secure"] = True


def read_refresh_cookie(request: HttpRequest) -> str | None:
    return request.COOKIES.get(settings.JWT_REFRESH_COOKIE)


# --- Django admin session --------------------------------------------------
def start_admin_session(request: HttpRequest, user: AbstractBaseUser) -> None:
    """Log the user into Django's session framework as well as issuing JWTs.

    The admin at /admin/ is server-rendered and authenticates from the session
    cookie; a JWT cookie means nothing to it. Rather than bolt a second
    authentication path onto the admin, we hand the *same* Django user to
    ``django.contrib.auth.login``. One user record, two credentials, both issued
    by the same request.

    ``login()`` cycles the session key, which is what closes session fixation:
    any session id the visitor arrived holding is discarded here.
    """
    login(request, user)


def end_admin_session(request: HttpRequest) -> None:
    logout(request)


# --- audit -----------------------------------------------------------------
def client_ip(request: HttpRequest) -> str:
    """Client address for the security log.

    ``X-Forwarded-For`` is read only when NUM_PROXIES says a proxy is actually
    in front, and then only the hop that proxy appended — a client can put
    anything in that header, and an audit trail of attacker-chosen addresses is
    worse than none. Uses the same setting as the throttles so the log and the
    rate limit always name the same host.
    """
    proxies = api_settings.NUM_PROXIES
    if proxies:
        hops = [h.strip() for h in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if h.strip()]
        if hops:
            return hops[-min(proxies, len(hops))]
    return request.META.get("REMOTE_ADDR", "?")
