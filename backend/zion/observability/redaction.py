"""What must never reach a Django log line.

Mirrors ``ai_service/app/core/redaction.py``; see the note in this package's
``__init__`` about why the two are separate copies rather than a shared library.

Secrets are replaced outright. Content — a document body, a question, an answer
— is reduced to a length and a hash instead, which keeps the field useful for
telling two values apart without making it readable.
"""

from __future__ import annotations

import hashlib
from typing import Any

REDACTED = "[redacted]"

_SECRET_HINTS: tuple[str, ...] = (
    "authorization",
    "auth",
    "cookie",
    "csrf",
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "api-key",
    "credential",
    "private_key",
    "session",
    "signature",
    "bearer",
)

_CONTENT_HINTS: tuple[str, ...] = (
    "text",
    "content",
    "prompt",
    "answer",
    "question",
    "query",
    "message",
    "body",
)

_MAX_VALUE_CHARS = 200
_MAX_DEPTH = 4

# Header names Django exposes on the WSGI environ, in their HTTP_ form.
_SENSITIVE_HEADERS = frozenset(
    {
        "HTTP_AUTHORIZATION",
        "HTTP_COOKIE",
        "HTTP_X_API_KEY",
        "HTTP_X_INTERNAL_TOKEN",
        "HTTP_PROXY_AUTHORIZATION",
    }
)


def _is_secret(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _SECRET_HINTS)


def _is_content(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _CONTENT_HINTS)


def summarize(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:12]
    return f"<{len(value)} chars sha256:{digest}>"


def redact_value(name: str, value: Any, _depth: int = 0) -> Any:
    if _is_secret(name):
        return REDACTED

    if isinstance(value, dict):
        if _depth >= _MAX_DEPTH:
            return f"<dict of {len(value)}>"
        return {str(k): redact_value(str(k), v, _depth + 1) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        if _depth >= _MAX_DEPTH:
            return f"<{type(value).__name__} of {len(value)}>"
        items = list(value)
        if len(items) > 10:
            return f"<{len(items)} items>"
        return [redact_value(name, item, _depth + 1) for item in items]

    if isinstance(value, str):
        if _is_content(name):
            return summarize(value)
        if len(value) > _MAX_VALUE_CHARS:
            return value[:_MAX_VALUE_CHARS] + f"…(+{len(value) - _MAX_VALUE_CHARS})"
        return value

    return value


def redact(payload: dict[str, Any]) -> dict[str, Any]:
    return {str(k): redact_value(str(k), v) for k, v in payload.items()}


def safe_headers(meta: dict[str, Any]) -> dict[str, str]:
    """Request headers from a WSGI environ, with the credential-bearing ones gone."""
    headers = {}
    for key, value in meta.items():
        if not key.startswith("HTTP_"):
            continue
        if key in _SENSITIVE_HEADERS or _is_secret(key):
            headers[key] = REDACTED
        else:
            headers[key] = str(value)[:_MAX_VALUE_CHARS]
    return headers
