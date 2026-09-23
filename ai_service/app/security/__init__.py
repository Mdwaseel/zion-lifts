"""The security pipeline, as four independent checks and one entry point.

Each module answers a different question and none of them knows about the
others:

    input_validation    is this string even a question?
    prompt_injection    is it trying to talk to the model instead of to us?
    abuse_detection     is it asking for something that hurts someone?
    output_guard        did anything leak on the way back?

:func:`inspect_request` runs the first three in the order that costs least and
refuses earliest, and returns a single verdict the router can act on. It is a
pure function over a string — no I/O, no model call — so it adds no measurable
latency to a request and can be exercised exhaustively in tests.

The reason it is one function rather than three calls at the call site is that
the *order* is part of the design: a string that is not a question should never
be scored for injection, and a jailbreak attempt should be reported as a
jailbreak rather than as whatever the abuse rules make of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.security import abuse_detection, input_validation, output_guard, prompt_injection
from app.security.abuse_detection import AbuseCategory


class ThreatKind(StrEnum):
    """What was found, and therefore which reply is owed."""

    NONE = "none"
    MALFORMED = "malformed"
    PROMPT_INJECTION = "prompt_injection"
    UNSAFE_PROCEDURE = "unsafe_procedure"
    HARMFUL = "harmful"
    ABUSIVE = "abusive"


@dataclass(slots=True, frozen=True)
class SecurityVerdict:
    """The outcome of inspecting one incoming question.

    ``question`` is the normalised form and is what every later stage should
    use. When ``blocked`` is false it is still the value to carry forward — the
    normalisation happened either way.
    """

    kind: ThreatKind
    question: str
    detail: str = ""

    @property
    def blocked(self) -> bool:
        return self.kind is not ThreatKind.NONE


_ABUSE_TO_THREAT = {
    AbuseCategory.UNSAFE_PROCEDURE: ThreatKind.UNSAFE_PROCEDURE,
    AbuseCategory.HARMFUL: ThreatKind.HARMFUL,
    AbuseCategory.ABUSIVE: ThreatKind.ABUSIVE,
}


def inspect_request(raw: str, max_chars: int | None = None) -> SecurityVerdict:
    """Validate, then scan for injection, then scan for abuse.

    Cheapest and most certain first. Injection is checked before abuse because
    an attack on the assistant and a dangerous request need different replies,
    and a jailbreak wrapped in lift vocabulary would otherwise be reported as
    the lift question it is pretending to be.
    """
    validation = (
        input_validation.validate_question(raw, max_chars)
        if max_chars is not None
        else input_validation.validate_question(raw)
    )
    question = validation.cleaned
    if not validation.ok:
        return SecurityVerdict(ThreatKind.MALFORMED, question, validation.reason)

    injection = prompt_injection.scan_user_input(question)
    if injection.blocks_request:
        return SecurityVerdict(ThreatKind.PROMPT_INJECTION, question, ",".join(injection.rules))

    abuse = abuse_detection.scan(question)
    if abuse.blocked:
        return SecurityVerdict(_ABUSE_TO_THREAT[abuse.category], question, str(abuse.category))

    return SecurityVerdict(ThreatKind.NONE, question)


__all__ = [
    "SecurityVerdict",
    "ThreatKind",
    "abuse_detection",
    "input_validation",
    "inspect_request",
    "output_guard",
    "prompt_injection",
]
