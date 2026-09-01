"""The one endpoint the public website calls.

Open by design — it is called by every visitor before anyone has signed in — and
therefore the most exposed surface in the project. Four things hold it:

* **Throttled** per IP, on its own scope, so it cannot be used to fill the
  table faster than a person could browse.
* **Bounded input.** Everything is length-capped and type-checked before it
  reaches a query; the path is stripped of its query string in
  ``services.normalise_path``.
* **Idempotent.** A repeated ``event_id`` is a no-op, so a retry cannot inflate
  a number.
* **Silent on failure.** A tracking error returns 202 and logs; it never
  surfaces to the visitor. Analytics is not worth a broken page.

It answers 202 rather than 201 throughout, including for duplicates: the honest
meaning is "received, and what happens next is not your concern", and the
browser cannot act on the difference anyway.
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import services

log = logging.getLogger(__name__)

MAX_REFERRER = 500
MAX_USER_AGENT = 400


class TrackView(APIView):
    """``POST /api/analytics/track`` — record one page view."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_scope = "analytics_track"

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}

        try:
            services.track(
                visitor_key=data.get("visitor_id"),
                event_key=data.get("event_id"),
                path=data.get("path"),
                # The body's referrer is preferred over the header: on a
                # single-page app the header still says whatever loaded the app
                # shell, while the body carries the referrer for *this* route
                # change, which is the thing being recorded.
                referrer=_clip(data.get("referrer") or request.META.get("HTTP_REFERER"), MAX_REFERRER),
                user_agent=_clip(request.META.get("HTTP_USER_AGENT"), MAX_USER_AGENT),
                request=request,
            )
        except services.TrackingRejected as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            # Anything else is our problem, not the visitor's. Logged with a
            # stack trace so it is visible in the request log, and swallowed so
            # the beacon never becomes an error in their console.
            log.exception("analytics: could not record a page view")

        return Response(status=status.HTTP_202_ACCEPTED)


def _clip(value, limit: int) -> str:
    return str(value)[:limit] if value else ""
