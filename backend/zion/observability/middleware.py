"""Request correlation and one structured completion record per request.

The middleware is deliberately thin. It resolves an id, times the request, and
writes a single line when it finishes; it does not touch the database, does not
serialise the body, and holds nothing between requests. Anything heavier here is
paid on every request the site serves, including the ones that were already
slow — which is the opposite of what observability is for.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from zion.observability.context import resolve_request_id, set_request_id

logger = logging.getLogger("zion.request")

# Infrastructure calls these constantly and their outcome is uninteresting until
# it changes. Logged at DEBUG so a health probe every five seconds does not bury
# the requests an operator is actually looking for.
_QUIET_PATHS = ("/health", "/healthz", "/api/health", "/ready", "/static/", "/media/")


class RequestObservabilityMiddleware:
    """Attach a correlation id, time the request, and record how it ended."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.header = getattr(settings, "REQUEST_ID_HEADER", "X-Request-ID")
        # Django exposes headers on the environ in this shape.
        self.meta_key = "HTTP_" + self.header.upper().replace("-", "_")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = resolve_request_id(request.META.get(self.meta_key))
        set_request_id(request_id)
        # Attached to the request so views, serializers and the dispatch layer
        # can read it without importing the context module.
        request.request_id = request_id  # type: ignore[attr-defined]

        started = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            # `process_exception` and the handler chain deal with the exception
            # itself; this records that the *request* ended badly, which is what
            # the error rate is counted from.
            logger.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "method": request.method,
                    "route": _route_of(request),
                    "duration_ms": round(duration_ms, 1),
                },
            )
            raise

        duration_ms = (time.perf_counter() - started) * 1000
        response[self.header] = request_id

        level = logging.INFO
        if _is_quiet(request.path):
            level = logging.DEBUG
        elif response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING

        logger.log(
            level,
            "request_completed",
            extra={
                "event": "request_completed",
                "method": request.method,
                # The route template and the path — never `request.GET`, which
                # is caller-controlled and is where a token ends up when
                # somebody puts one in a URL.
                "route": _route_of(request),
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 1),
                "user_id": _user_id(request),
            },
        )
        return response


def _is_quiet(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _QUIET_PATHS)


def _route_of(request: HttpRequest) -> str:
    """The URL pattern, not the resolved path.

    `/api/knowledge/documents/<uuid:pk>/` rather than the id it matched. The
    concrete path identifies one document; the pattern identifies the endpoint,
    which is the thing worth grouping by.
    """
    match = getattr(request, "resolver_match", None)
    if match is not None and match.route:
        return str(match.route)
    return "unmatched"


def _user_id(request: HttpRequest) -> str | None:
    """The acting user's id, or None. Never their email or name.

    An id in a log line is a join key an operator with database access can
    resolve; an email address in a log line is personal data in a system with a
    different retention policy from the database.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return str(user.pk)
