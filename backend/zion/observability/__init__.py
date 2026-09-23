"""Request correlation, structured logging and redaction for the Django side.

A deliberate near-duplicate of ``ai_service/app/core/{logging,redaction}.py``.
The two are separate processes in separate images with no shared package, so the
alternative to writing it twice is publishing a library for two hundred lines of
code — and a shared library that both services must upgrade in lockstep is a
worse coupling than a little repetition.

What is *not* duplicated is the metrics registry. Django's operational numbers —
how many jobs are running, failed, stale — are rows in Postgres, and Postgres is
already the source of truth for them. Counting them a second time in memory
would produce a second answer that disagrees after every restart.
"""

from zion.observability.context import get_request_id, new_request_id, set_request_id

__all__ = ["get_request_id", "new_request_id", "set_request_id"]
