"""Rate limits for the authentication endpoints.

Two axes, because they stop different attacks:

* per IP  — one host hammering the login form (``login`` / ``captcha`` scopes);
* per account — a slow spread of guesses against one address from many hosts,
  which no per-IP limit would ever see.

Both are configurable; the defaults are loose enough that a person mistyping
their password four times in a row is unaffected.

Note that all of this depends on ``NUM_PROXIES`` being right in settings: it is
what decides whether the per-IP bucket is keyed on the real client address or on
a header the client controls.
"""

from __future__ import annotations

import hashlib

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class LoginIPThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class CaptchaThrottle(SimpleRateThrottle):
    scope = "captcha"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginAccountThrottle(SimpleRateThrottle):
    """Caps *failed* attempts against a single email address, wherever they come from.

    Only failures count: the view calls ``record_failure`` after the fact, so
    someone signing in correctly ten times in a day is never locked out by their
    own success.

    The count is a single integer bumped with ``incr`` rather than DRF's list of
    timestamps. A list would have to be read, appended to and written back, and
    fifty simultaneous failures would then each write back a list one longer
    than the one they read — the bucket would end up holding two entries instead
    of fifty, and the cap would not bind against exactly the parallel attack it
    exists to stop. ``incr`` is atomic on both the locked LocMemCache and Redis.

    The trade-off is a fixed window rather than DRF's sliding one: the count
    resets when the first failure in the window expires. For a lockout counter
    that is the right shape anyway.
    """

    scope = "login_account"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        # request.data is client-controlled: {"email": 5} or {"email": [...]} must
        # not raise here, or the throttle turns a 400 into a 500.
        if not isinstance(email, str) or not email.strip():
            return None

        # Hashed, so the throttle cache does not become a list of the site's
        # administrator addresses. Normalised the same way the serializer and
        # the auth backend normalise it, so case and padding cannot evade it.
        ident = hashlib.sha256(
            f"{settings.SECRET_KEY}{email.strip().lower()}".encode()
        ).hexdigest()[:32]
        return self.cache_format % {"scope": self.scope, "ident": ident}

    def allow_request(self, request, view):
        """Read the bucket without spending from it; the view records failures."""
        self.key = self.get_cache_key(request, view)
        if self.key is None or self.rate is None:
            return True

        self.failures = self.cache.get(self.key, 0)
        return self.failures < self.num_requests

    def record_failure(self, request, view) -> None:
        key = self.get_cache_key(request, view)
        if key is None or self.rate is None:
            return

        try:
            self.cache.incr(key)
        except ValueError:  # no counter yet for this window
            if not self.cache.add(key, 1, self.duration):
                # Another request created it in between — count against theirs.
                try:
                    self.cache.incr(key)
                except ValueError:
                    pass

    def wait(self) -> float:
        """Seconds to advertise in Retry-After.

        The window is fixed, so the honest answer without storing a deadline is
        the full window: never shorter than the real wait.
        """
        return self.duration
