"""Log formatters that carry the correlation id and scrub their own fields.

Redaction lives in the formatter rather than at the call sites, for the same
reason it does on the ai_service side: a policy that every ``logger.info`` has
to remember holds until the first hurried change, while a formatter applies to
lines written years later by people who never read this file.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from zion.observability.context import get_request_id
from zion.observability.redaction import redact_value

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}

SERVICE = "backend"


class RequestIdFilter(logging.Filter):
    """Attach the current correlation id to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return True


def _extras(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: redact_value(key, value)
        for key, value in record.__dict__.items()
        if key not in _RESERVED and not key.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """One JSON object per line, matching the shape ai_service emits.

    The two services share the field names — ``service``, ``event``,
    ``request_id``, ``duration_ms`` — on purpose. One upload crosses both, and a
    query that has to be written twice because each side spells the correlation
    field differently is a query nobody writes.
    """

    def format(self, record: logging.LogRecord) -> str:
        extras = _extras(record)
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": SERVICE,
            "logger": record.name,
            "request_id": extras.pop("request_id", None) or get_request_id(),
            "event": extras.pop("event", None) or record.getMessage(),
            "message": record.getMessage(),
        }
        payload.update(extras)
        if record.exc_info:
            # Tracebacks go to the log. They never go to an API response.
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable, and redacted all the same — a developer's terminal is
    still somewhere a token can be copied out of."""

    def __init__(self) -> None:
        super().__init__(
            "{asctime} {levelname:<8} [{request_id}] {name}: {message}",
            style="{",
        )

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        base = super().format(record)
        extras = {k: v for k, v in _extras(record).items() if k != "request_id"}
        if not extras:
            return base
        return f"{base} | " + " ".join(f"{k}={v}" for k, v in extras.items())
