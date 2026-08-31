"""Logging setup plus a request-scoped correlation id.

Redaction happens in the formatter, not at the call sites. Asking every
``logger.info`` to remember to scrub its own fields is a policy that holds until
the first hurried change; putting it here means a field added to an ``extra``
dict next year is scrubbed by code written today. Call sites are still expected
not to pass secrets — this is the second line, not the first.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from app.core.redaction import redact_value

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}

# Identifies which process wrote the line once the API and the worker are
# shipping into the same place. Set by `configure_logging`.
_service_name = "ai_service"
_environment = "development"


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the extras redacted.

    ``message`` doubles as ``event`` when a call site passed no explicit one, so
    a line written before the vocabulary existed still has the field queries
    filter on.
    """

    def format(self, record: logging.LogRecord) -> str:
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                extras[key] = redact_value(key, value)

        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": _service_name,
            "environment": _environment,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "event": extras.pop("event", None) or record.getMessage(),
            "message": record.getMessage(),
        }
        payload.update(extras)
        if record.exc_info:
            # The traceback goes to the log, never to an API response.
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """The human-readable form, for development.

    Redacts too. A developer's terminal is still somewhere a token can be
    copied out of, and the local .env holds real credentials.
    """

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            key: redact_value(key, value)
            for key, value in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_") and key != "request_id"
        }
        if not extras:
            return base
        rendered = " ".join(f"{k}={v}" for k, v in extras.items())
        return f"{base} | {rendered}"


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
    service: str = "ai_service",
    environment: str = "development",
) -> None:
    global _service_name, _environment
    _service_name = service
    _environment = environment

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JsonFormatter() if json_output else ConsoleFormatter())

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())

    for noisy in ("httpx", "httpcore", "urllib3", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
