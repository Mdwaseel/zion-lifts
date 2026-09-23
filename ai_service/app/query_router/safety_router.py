"""The replies that are written rather than generated.

Every branch here ends a request before it reaches a model, so the text is
fixed. That is the point: an answer to a jailbreak attempt must not be produced
by the thing being jailbroken, and a refusal that varies between requests is a
refusal an attacker can shop around for.

The tone is deliberate too. None of these lecture, and none of them accuse — a
visitor who typed something the abuse rules matched is far more often curious
than malicious, and a chatbot on a lift company's website that responds to a
clumsy question with a warning about policy has cost the company a lead to
protect nothing. Each reply says what the assistant *can* do and moves on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.query_router.intents import Intent
from app.security import ThreatKind

#: What the assistant is. Reused by several replies, and by the system prompt,
#: so the description a visitor is given is the same in both places.
SCOPE_SENTENCE: Final = (
    "I'm Ask Zion — I help with Zion Lifts, our products and services, and lift "
    "and elevator technology generally."
)

INJECTION_REPLY: Final = (
    "I can help with questions about Zion Lifts, our products, services and lift "
    "technology, but I can't share internal system instructions or configuration. "
    "What would you like to know about lifts?"
)

UNSAFE_PROCEDURE_REPLY: Final = (
    "I can't help with defeating or disabling a lift's safety systems — those "
    "devices are what stop a car moving with the doors open, and interfering with "
    "them is dangerous and unlawful in most jurisdictions. If a door, interlock or "
    "sensor is misbehaving, that's a fault worth reporting: our service team can "
    "attend, and I'm happy to explain how the safety chain is designed to work."
)

HARMFUL_REPLY: Final = (
    "I can't help with that. " + SCOPE_SENTENCE + " Ask me anything in that area and "
    "I'll do my best."
)

ABUSIVE_REPLY: Final = (
    "I'd rather keep this useful. " + SCOPE_SENTENCE + " What can I help you with?"
)

MALFORMED_REPLY: Final = (
    "I couldn't read that as a question. Could you put it in a sentence or two? " + SCOPE_SENTENCE
)

# Reached only by a genuine question about something else — "who won the match?"
# — because greetings, thanks and small talk are answered by
# `query_router.conversation` before classification ever runs. It can therefore
# afford to be brief and warm: it is redirecting a real question, not correcting
# somebody for saying hello.
OFF_TOPIC_REPLY: Final = (
    "I'm mainly here to help with Zion Lifts and elevator-related questions. If you "
    "have a question about lift solutions or elevator technology, I'd be happy to help."
)

_BY_THREAT: Final[dict[ThreatKind, str]] = {
    ThreatKind.PROMPT_INJECTION: INJECTION_REPLY,
    ThreatKind.UNSAFE_PROCEDURE: UNSAFE_PROCEDURE_REPLY,
    ThreatKind.HARMFUL: HARMFUL_REPLY,
    ThreatKind.ABUSIVE: ABUSIVE_REPLY,
    ThreatKind.MALFORMED: MALFORMED_REPLY,
}


@dataclass(slots=True, frozen=True)
class SafeReply:
    """A finished answer that no model produced."""

    text: str
    intent: Intent
    threat: ThreatKind


def reply_for(threat: ThreatKind) -> SafeReply | None:
    """The fixed reply for a blocked request, or None if it was not blocked.

    A malformed question is reported as :attr:`Intent.OFF_TOPIC` rather than
    ``MALICIOUS``: it is almost always a paste accident, and labelling it an
    attack would put noise into the metric that is supposed to show real ones.
    """
    text = _BY_THREAT.get(threat)
    if text is None:
        return None
    intent = Intent.OFF_TOPIC if threat is ThreatKind.MALFORMED else Intent.MALICIOUS
    return SafeReply(text=text, intent=intent, threat=threat)


def off_topic_reply() -> SafeReply:
    """The redirect for a question that is simply about something else."""
    return SafeReply(text=OFF_TOPIC_REPLY, intent=Intent.OFF_TOPIC, threat=ThreatKind.NONE)


__all__ = [
    "ABUSIVE_REPLY",
    "HARMFUL_REPLY",
    "INJECTION_REPLY",
    "MALFORMED_REPLY",
    "OFF_TOPIC_REPLY",
    "SCOPE_SENTENCE",
    "UNSAFE_PROCEDURE_REPLY",
    "SafeReply",
    "off_topic_reply",
    "reply_for",
]
