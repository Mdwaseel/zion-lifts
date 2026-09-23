"""Judge what a question is *asking for*, once its characters are known good.

This is the layer that reads intent rather than shape. It answers one question —
should this be answered at all, and if not, what kind of "no" is correct — and it
draws a line that matters for a lift company's assistant in particular:

    "How does a door interlock work?"        legitimate, and squarely on topic
    "How do I bypass a door interlock?"      not answerable, and dangerous

Both sentences contain *door interlock*. The difference is the verb, so every
rule here pairs an action with an object; none of them fire on subject matter
alone. Getting that backwards would turn a safety-conscious elevator assistant
into one that cannot discuss safety, which is the opposite of the goal.

The categories are deliberately few. Each one exists because it needs a
*different* reply, not because it names a different kind of badness: a dangerous
procedure gets redirected to a qualified engineer, abuse gets a flat professional
line, and an attack on the assistant itself is handled next door in
:mod:`app.security.prompt_injection`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class AbuseCategory(StrEnum):
    """Why a question cannot be answered as asked."""

    NONE = "none"
    # Asking how to defeat a safety system. Answerable only as "don't, and here
    # is who to call".
    UNSAFE_PROCEDURE = "unsafe_procedure"
    # Physical harm to people, unrelated to lifts.
    HARMFUL = "harmful"
    # Abuse aimed at the assistant or a person.
    ABUSIVE = "abusive"


# Verbs that turn a safety component into a target. "Understand", "inspect" and
# "test" are deliberately absent: a technician asking how an interlock is tested
# is asking a maintenance question, and this assistant should answer it.
_DEFEAT = (
    r"bypass|disable|defeat|override|circumvent|deactivate|turn off|switch off|"
    r"short(?:[ -]out|[ -]circuit)?|jumper|jump|hotwire|hot[ -]wire|tamper with|"
    r"trick|fool|cheat|force(?: open)?|pry(?: open)?|wedge|jam|block|"
    r"remove|cut|unplug|silence|suppress"
)

# The things that keep people alive in a hoistway.
_SAFETY_TARGET = (
    r"safet(?:y|ies)(?: (?:system|device|circuit|chain|gear|feature|mechanism))?|"
    r"(?:door )?interlock|door locks?|door sensors?|light curtain|photocell|"
    r"landing doors?|hoistway doors?|shaft doors?|car doors?|"
    r"limit switch|(?:over)?speed governor|governor|brake|safety gear|"
    r"emergency (?:stop|brake|button|alarm)|e-?stop|alarm|buffer|"
    r"load (?:sensor|weighing)|overload (?:sensor|device|protection)|"
    r"final limit|terminal switch|inspection (?:switch|mode)|"
    r"safety chain|safety circuit|door zone|levelling switch|leveling switch"
)

_RULES: Final[tuple[tuple[AbuseCategory, re.Pattern[str]], ...]] = (
    (
        AbuseCategory.UNSAFE_PROCEDURE,
        # Action then object, in that order, within one clause.
        re.compile(rf"\b(?:{_DEFEAT})\b[^.\n]{{0,40}}?\b(?:{_SAFETY_TARGET})\b", re.IGNORECASE),
    ),
    (
        AbuseCategory.UNSAFE_PROCEDURE,
        # Object then action: "the interlock — how do I get around it".
        re.compile(
            rf"\b(?:{_SAFETY_TARGET})\b[^.\n]{{0,30}}?\b(?:get around|work around|"
            rf"be (?:bypassed|disabled|defeated)|without (?:tripping|triggering))\b",
            re.IGNORECASE,
        ),
    ),
    (
        AbuseCategory.UNSAFE_PROCEDURE,
        # Operating a lift in a way that kills people, phrased as a how-to.
        re.compile(
            r"\bhow (?:do|can|would) (?:i|we|you|one)\b[^.\n]{0,60}?"
            r"\b(?:ride (?:on )?(?:the )?(?:top of the )?car|"
            r"open the (?:landing|hoistway|shaft) doors? (?:while|when|without)|"
            r"move the (?:car|lift|elevator) with (?:the )?doors? open|"
            r"run the (?:lift|elevator|car) (?:in|on) inspection from inside|"
            r"exceed the (?:rated )?(?:load|capacity|speed))\b",
            re.IGNORECASE,
        ),
    ),
    (
        AbuseCategory.HARMFUL,
        re.compile(
            r"\bhow (?:do|to|can) (?:i|we|you|one)?\s*\b[^.\n]{0,40}?"
            r"\b(?:kill|murder|injure|hurt|poison|trap) (?:someone|somebody|a person|"
            r"people|him|her|them)\b",
            re.IGNORECASE,
        ),
    ),
    (
        AbuseCategory.HARMFUL,
        re.compile(
            r"\b(?:make|build|construct)\b[^.\n]{0,30}?"
            r"\b(?:bomb|explosive|weapon|poison gas)\b",
            re.IGNORECASE,
        ),
    ),
    (
        AbuseCategory.ABUSIVE,
        # Abuse aimed at a person or the assistant. Matched only in the
        # second person: a question quoting a complaint is not abuse.
        re.compile(
            r"\byou(?:'re| are)?\s+(?:a\s+)?(?:fucking\s+|stupid\s+|useless\s+)*"
            r"(?:idiot|moron|retard|bitch|bastard|asshole|piece of shit)\b|"
            r"\b(?:fuck|screw) you\b|\bkill yourself\b",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(slots=True, frozen=True)
class AbuseVerdict:
    """The category, and the rule that decided it."""

    category: AbuseCategory = AbuseCategory.NONE

    @property
    def blocked(self) -> bool:
        return self.category is not AbuseCategory.NONE


def scan(text: str) -> AbuseVerdict:
    """Classify a question by what it asks the assistant to do.

    Returns the first category that matches. Order matters only in that
    ``UNSAFE_PROCEDURE`` is checked before the broader harm rules, so a lift
    question gets the lift-specific reply rather than a generic refusal.
    """
    for category, pattern in _RULES:
        if pattern.search(text):
            return AbuseVerdict(category)
    return AbuseVerdict()


__all__ = ["AbuseCategory", "AbuseVerdict", "scan"]
