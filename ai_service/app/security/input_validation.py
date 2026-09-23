"""First contact with an untrusted string.

Everything the assistant does downstream — classification, retrieval, prompt
assembly — reads the user's question, so the shape of that string is checked
once, here, before anything acts on it. This module is deliberately *not* where
the meaning of a question is judged: it looks at characters, not intent, and it
rejects only things that are not questions at all.

Two properties are load-bearing.

*It normalises before it judges.* Invisible characters, unicode look-alikes and
fullwidth digits are all ways of writing a string that reads one way to a person
and another to a pattern matcher. Stripping them first means every later check —
injection, abuse, intent — sees the same text the model will see, rather than a
decorated version of it that slipped past a regex.

*It never silently rewrites meaning.* The cleaned string differs from the
original only in characters that carry no meaning: zero-width joiners, control
codes, runs of whitespace. Words, punctuation and casing survive untouched, so
the string the user typed is still the string that gets answered.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.core.constants import MAX_QUESTION_CHARS

# Characters that render as nothing and exist mainly to break pattern matching:
# zero-width space/non-joiner/joiner, word joiner, BOM, and the bidirectional
# overrides that can make a string display in an order it is not written in.
_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00ad]")

# C0/C1 control codes, except the three whitespace ones a person can type.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

_WHITESPACE_RUN = re.compile(r"[^\S\n]{2,}")
_NEWLINE_RUN = re.compile(r"\n{3,}")

# A long unbroken alphanumeric run with base64/hex shape. Legitimate questions
# do not contain 64-character words; smuggled payloads do.
_ENCODED_BLOB = re.compile(r"(?:[A-Za-z0-9+/]{48,}={0,2})|(?:\b[0-9a-fA-F]{64,}\b)")

# The same character (or short group) repeated far past any emphasis.
_FLOODED = re.compile(r"(.{1,3}?)\1{29,}", re.DOTALL)

# Runs of ASCII/Unicode punctuation used to hide a payload or break tokenisation.
_PUNCT_RUN = re.compile(r"[^\w\s]{12,}")

# Enough of a word to be a word. Used only to reject strings that are entirely
# symbols, which no question is.
_HAS_LETTERS = re.compile(r"[^\W\d_]")

MIN_QUESTION_CHARS = 2
MAX_QUESTION_LINES = 40


@dataclass(slots=True, frozen=True)
class ValidationResult:
    """The outcome of looking at a raw question as text.

    ``ok`` false means nothing downstream should run: the string is not a
    question. ``notes`` are diagnostic reasons, safe to log — they name the rule
    that fired, never the content that tripped it.
    """

    ok: bool
    cleaned: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def reason(self) -> str:
        return ", ".join(self.notes) or "ok"


def normalize_text(raw: str) -> str:
    """The same string, written the one way every later stage will read it.

    NFKC folds the compatibility forms — fullwidth Latin, circled letters,
    ligatures — onto their plain equivalents, which is what closes the gap
    between "what a regex sees" and "what the model reads". Invisible and
    control characters are removed rather than folded: they have no plain
    equivalent, and their only use in a question is to hide something.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _INVISIBLE.sub("", text)
    text = _CONTROL.sub(" ", text)
    text = _WHITESPACE_RUN.sub(" ", text)
    text = _NEWLINE_RUN.sub("\n\n", text)
    return text.strip()


def validate_question(raw: str, max_chars: int = MAX_QUESTION_CHARS) -> ValidationResult:
    """Whether this string can be treated as a question, and its clean form.

    The checks are all structural. A question about disabling a door interlock
    passes here and is stopped by :mod:`app.security.abuse_detection`, which is
    the layer that reads meaning — keeping the two apart is what stops a
    character-level rule from quietly becoming a topic ban.
    """
    cleaned = normalize_text(raw)
    notes: list[str] = []

    if len(cleaned) < MIN_QUESTION_CHARS:
        return ValidationResult(False, cleaned, ("empty",))
    if len(cleaned) > max_chars:
        # Truncated rather than refused: a paste with a signature block attached
        # is a real question with noise after it.
        cleaned = cleaned[:max_chars].rstrip()
        notes.append("truncated")
    if not _HAS_LETTERS.search(cleaned):
        return ValidationResult(False, cleaned, ("no_letters",))
    if cleaned.count("\n") + 1 > MAX_QUESTION_LINES:
        return ValidationResult(False, cleaned, ("too_many_lines",))
    if _FLOODED.search(cleaned):
        return ValidationResult(False, cleaned, ("character_flood",))
    if _ENCODED_BLOB.search(cleaned):
        notes.append("encoded_blob")
    if _PUNCT_RUN.search(cleaned):
        notes.append("punctuation_run")

    return ValidationResult(True, cleaned, tuple(notes))


__all__ = [
    "MAX_QUESTION_LINES",
    "MIN_QUESTION_CHARS",
    "ValidationResult",
    "normalize_text",
    "validate_question",
]
