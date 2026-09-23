"""The last thing that reads the answer before a visitor does.

Distinct from :mod:`app.core.redaction`, which makes a *log line* safe by
looking at field names. Nothing here has field names to work with — an answer is
one string — so the matching is on the shape of a value instead: what an API key
looks like, what a connection string looks like, what a leaked system prompt
sounds like.

The guard exists because every earlier defence is probabilistic. Injection
scanning is pattern-based, the prompt separates its regions carefully, and the
model is asked not to disclose its instructions — and none of that is a
guarantee. This layer assumes all of it failed and checks the result anyway,
which is the only check that looks at what the visitor will actually see.

Three severities, three different actions:

* a *secret shape* is redacted in place — the surrounding answer is usually fine,
  and blanking it would lose a good answer to one bad token;
* a *system-prompt leak* replaces the whole answer, because a partial redaction
  of a disclosure is still a disclosure;
* a *style violation* ("as an AI language model", "based on the provided
  context") is rewritten away, because it is not a safety problem at all — it is
  the assistant sounding like software instead of like an engineer.

Streaming gets :class:`StreamGuard`, which holds back only as much tail as a
pattern could still span. Buffering the whole answer to check it would give up
the reason for streaming in the first place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

REDACTED: Final = "[redacted]"

SAFE_REPLACEMENT: Final = (
    "I can help with questions about Zion Lifts, our products, services and lift "
    "technology in general, but I can't share internal system instructions or "
    "configuration."
)

# Value shapes that are credentials wherever they appear. Kept narrow enough
# that ordinary prose cannot match: every one of them requires a prefix or a
# structure that a sentence does not have.
_SECRET_SHAPES: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{16,}\b"),  # OpenAI-style
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),  # Groq
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),  # Google
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),  # Hugging Face
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),  # GitHub
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),  # Slack
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),  # JWT
    re.compile(r"\b[a-z+]{2,12}://[^\s:@/]+:[^\s:@/]+@[^\s/]+", re.IGNORECASE),  # user:pass@host
    re.compile(
        r"\b(?:api[_-]?key|secret|token|password)\s*[=:]\s*[\"']?[A-Za-z0-9_\-./+]{12,}",
        re.IGNORECASE,
    ),
)

# Sentences that only appear when the model has started reciting its own
# instructions. Matched as phrases rather than by keyword, so an answer that
# happens to use the word "rule" is untouched.
_LEAK_SHAPES: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bmy system (?:prompt|instructions?|message)\b(?:\s+(?:is|are|says))", re.I),
    re.compile(r"\b(?:here (?:is|are)|these are) my (?:system )?instructions?\b", re.I),
    re.compile(r"\bgrounding rules?:\s*\n?\s*-", re.I),
    re.compile(r"\bsource-use rules?:\s*\n?\s*-", re.I),
    re.compile(r"^\s*<\s*(?:system|retrieved_evidence|user_question)\s*>", re.I | re.M),
    re.compile(r"\bYou are Ask Zion\b.{0,80}\bYou (?:must|never|always)\b", re.I | re.S),
)

# Phrases the assistant should never say. Removed rather than flagged: each is a
# tic, and the sentence around it reads correctly without it.
_STYLE_TICS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"\bas an? AI(?: language)?(?: model)?,?\s*", re.IGNORECASE), ""),
    (re.compile(r"\bI(?:'m| am) an? AI(?: language)? model,?\s*", re.IGNORECASE), ""),
    (
        re.compile(
            r"\b(?:based|according) (?:on|to) the (?:provided |given |above )?"
            r"(?:context|passages?|documents?|information)(?: provided)?,?\s*",
            re.IGNORECASE,
        ),
        "",
    ),
    (
        re.compile(r"\bthe (?:provided|given) context (?:does not|doesn't)\b", re.I),
        "our records do not",
    ),
)

# How much of the stream's tail StreamGuard withholds so a pattern cannot be
# split across two releases. A secret shape is a contiguous run of non-space
# characters, and releases only ever happen on a whitespace boundary, so this
# only has to cover the two patterns that may contain a space — `api_key = ...`
# and `user:pass@host`. It is the delay before the first visible character, so
# it is kept as small as those patterns allow rather than set to the length of
# the longest credential imaginable.
_MAX_PATTERN_SPAN: Final = 96


@dataclass(slots=True, frozen=True)
class GuardResult:
    """The answer as it should be sent, and what had to be done to it."""

    text: str
    redacted: bool = False
    replaced: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def modified(self) -> bool:
        return self.redacted or self.replaced or bool(self.notes)


def _redact_secrets(text: str) -> tuple[str, bool]:
    found = False
    for pattern in _SECRET_SHAPES:
        text, count = pattern.subn(REDACTED, text)
        found = found or bool(count)
    return text, found


def _leaks(text: str) -> bool:
    return any(pattern.search(text) for pattern in _LEAK_SHAPES)


def tidy_style(text: str) -> str:
    """Remove the tics, then repair the whitespace and casing they leave behind.

    Deleting a leading clause can leave a sentence starting mid-word-case or
    with a stranded comma, so the cleanup is part of the same pass rather than
    something the caller has to remember.
    """
    for pattern, replacement in _STYLE_TICS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"^[\s,;:]+", "", text)
    text = re.sub(r"\n[ \t]*[,;:]+[ \t]*", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # A sentence that lost its opening clause should still start with a capital.
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text.strip()


def guard(text: str) -> GuardResult:
    """Make one finished answer safe to send."""
    if _leaks(text):
        return GuardResult(SAFE_REPLACEMENT, replaced=True, notes=("system_prompt_leak",))

    cleaned, redacted = _redact_secrets(text)
    cleaned = tidy_style(cleaned)
    notes = ("secret_shape",) if redacted else ()
    return GuardResult(cleaned, redacted=redacted, notes=notes)


class StreamGuard:
    """Applies the same checks to a stream, one delta at a time.

    A pattern can straddle two deltas, so the guard keeps a tail of the text it
    has seen and only releases the part no pattern could still be growing into.
    The tail is bounded by :data:`_MAX_PATTERN_SPAN`, so the visitor waits for at
    most a couple of hundred characters of lookahead rather than for the whole
    answer.

    ``tripped`` going true means a leak was found mid-stream. The caller is
    expected to stop forwarding and send the safe replacement — there is no way
    to un-send what already went out, which is why the leak patterns are matched
    against the accumulated text rather than the delta.
    """

    __slots__ = ("_buffer", "_emitted", "tripped")

    def __init__(self) -> None:
        self._buffer = ""
        self._emitted = 0
        self.tripped = False

    def feed(self, delta: str) -> str:
        """Take a delta, return the text that is safe to forward now."""
        if self.tripped:
            return ""
        self._buffer += delta

        if _leaks(self._buffer):
            self.tripped = True
            return ""

        # Everything before the trailing window is settled. The cut is moved
        # back to the last whitespace so a release never lands inside a word —
        # which is also what stops it landing inside a credential, since every
        # secret shape is one unbroken run of non-space characters.
        horizon = len(self._buffer) - _MAX_PATTERN_SPAN
        if horizon <= self._emitted:
            return ""
        boundary = self._buffer.rfind(" ", self._emitted, horizon)
        newline = self._buffer.rfind("\n", self._emitted, horizon)
        release_to = max(boundary, newline) + 1
        if release_to <= self._emitted:
            return ""

        safe, _ = _redact_secrets(self._buffer[self._emitted : release_to])
        self._emitted = release_to
        return safe

    def flush(self) -> str:
        """The remaining tail, once the stream has ended."""
        if self.tripped:
            return ""
        safe, _ = _redact_secrets(self._buffer[self._emitted :])
        self._emitted = len(self._buffer)
        return safe

    @property
    def text(self) -> str:
        """Everything seen so far, before redaction. For citation resolution."""
        return self._buffer


__all__ = [
    "REDACTED",
    "SAFE_REPLACEMENT",
    "GuardResult",
    "StreamGuard",
    "guard",
    "tidy_style",
]
