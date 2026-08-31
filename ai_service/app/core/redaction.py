"""What must never reach a log line, and how it is removed.

Two different problems live here and they need different answers.

*Secrets* are the easy one. A field called ``authorization`` or ``api_key`` is
never wanted at any verbosity, so it is replaced with a marker. The matching is
by substring and case-insensitive, because the name that leaks is always the one
spelled slightly differently from the list — ``X-Api-Key``, ``apiKey``,
``gemini_api_key`` all have to go.

*Private content* is the harder one, because it is not identifiable by name. A
document's text, a user's question and a model's answer are all just strings on
fields called ``text`` or ``content``. Those are not redacted to a marker —
they are reduced to a *shape*: a length and a hash. That keeps the field useful
for the thing it is actually needed for (did the same text arrive twice? is this
chunk empty?) while making it useless for reading someone's document.

The rule that follows from the second point, and the one worth remembering:
never assume a container is safe because of its name. ``metadata`` is exactly
where a caller puts the thing you did not expect, so it is walked like anything
else rather than passed through.
"""

from __future__ import annotations

import hashlib
from typing import Any

REDACTED = "[redacted]"

# Substring matches, lower-cased. Deliberately broad: a false positive costs a
# field in a log line, a false negative costs a credential in one.
_SECRET_HINTS: tuple[str, ...] = (
    "authorization",
    "auth",
    "cookie",
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

# Fields whose value is content rather than a credential. Summarised, not
# removed — see the module docstring.
_CONTENT_HINTS: tuple[str, ...] = (
    "text",
    "content",
    "prompt",
    "answer",
    "question",
    "query",
    "message",
    "body",
    "passage",
    "chunk",
    "context",
    "completion",
)

# Long strings on unrecognised fields are truncated rather than trusted: an
# unbounded log line is its own problem, and a field nobody anticipated is
# exactly where a document body ends up.
_MAX_VALUE_CHARS = 200

# A nested structure deeper than this is not being read by a human anyway.
_MAX_DEPTH = 4


def _is_secret(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _SECRET_HINTS)


def _is_content(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _CONTENT_HINTS)


def summarize(value: str) -> str:
    """A string's shape, without the string.

    The hash is short and unsalted on purpose: it exists to tell two values
    apart across log lines, not to withstand an attempt to recover the original.
    Anything needing that guarantee should not have been near a log line.
    """
    digest = hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:12]
    return f"<{len(value)} chars sha256:{digest}>"


def redact_value(name: str, value: Any, _depth: int = 0) -> Any:
    """One field, made safe to log."""
    if _is_secret(name):
        return REDACTED

    if isinstance(value, dict):
        if _depth >= _MAX_DEPTH:
            return f"<dict of {len(value)}>"
        return {str(k): redact_value(str(k), v, _depth + 1) for k, v in value.items()}

    if isinstance(value, list | tuple | set):
        if _depth >= _MAX_DEPTH:
            return f"<{type(value).__name__} of {len(value)}>"
        # Sequences are summarised by length beyond a handful: a list of 900
        # chunks in a log line helps nobody and costs a megabyte.
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
    """A whole log-extra dict, made safe."""
    return {str(k): redact_value(str(k), v) for k, v in payload.items()}


def redact_headers(headers: Any) -> dict[str, str]:
    """Request headers with every credential-bearing one removed.

    Headers get their own function because they are the highest-risk source in
    the codebase — every request carries an ``Authorization`` — and because they
    arrive as a multidict rather than a plain dict.
    """
    try:
        items = headers.items()
    except AttributeError:  # pragma: no cover - defensive
        return {}
    return {str(k): (REDACTED if _is_secret(str(k)) else str(v)) for k, v in items}
