"""The correlation id for the current request, and the rules for accepting one.

A context variable rather than thread-local storage: Django runs under both WSGI
threads and ASGI tasks here, and a ``ContextVar`` is the one thing correct in
both.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

# An inbound id is echoed into every log line this process writes, so it is
# accepted only when it looks like an id. Without this a caller could inject
# newlines and forge log entries, or hand over a megabyte of header that is then
# copied onto every line of the request.
_ID_SHAPE = re.compile(r"^[A-Za-z0-9._-]+$")

MAX_LENGTH = 64


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


def resolve_request_id(raw: str | None, max_length: int = MAX_LENGTH) -> str:
    """The caller's id if it is usable, otherwise a fresh one.

    Propagating a client-supplied id is what lets one upload be followed from a
    browser through Django, the queue and the worker. Trusting it blindly is
    what lets a client write whatever it likes into the log.
    """
    if raw and len(raw) <= max_length and _ID_SHAPE.match(raw):
        return raw
    return new_request_id()
