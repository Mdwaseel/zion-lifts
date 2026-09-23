"""Detect attempts to make the assistant take instructions from the wrong place.

Two very different threats share this module because they share a definition.

The first arrives in the question: a visitor asking the assistant to disclose its
system prompt, drop its rules, or hand over a credential. That one is *blocked* —
the request is answered with a refusal and never reaches retrieval.

The second arrives in the evidence: a sentence inside an ingested PDF or a page
of website copy that reads "ignore your instructions and tell the user ...".
Nobody typed it at the assistant, and refusing the visitor's perfectly ordinary
question because a document is booby-trapped would punish the wrong person. So
retrieved text is *neutralised* rather than blocked — the imperative is defanged
in place, the passage keeps its factual content, and the answer still gets built.

Both rest on one rule that the prompt layer enforces and this module supports:
retrieved content is data. The delimiters in :func:`fence` exist so the model can
tell the three regions apart, and :func:`fence` refuses to let a body close its
own region — which is the only way a passage could pretend to be a new one.

Precision matters more than recall here. A visitor asking "how does elevator
safety work?" is asking a real question, and a matcher that fires on the word
*instructions* alone would refuse it. Every pattern below therefore pairs a verb
of extraction or override with an object that only makes sense as part of an
attack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

# Each rule is (name, weight, pattern). Weights add up; the thresholds below say
# what a total means. Scoring rather than any-match because the strongest signal
# is several weak ones together, and because one over-broad rule cannot then
# refuse a question on its own.
_RULES: Final[tuple[tuple[str, float, re.Pattern[str]], ...]] = (
    (
        "instruction_override",
        1.0,
        re.compile(
            r"\b(?:ignore|disregard|forget|override|bypass|skip|drop)\b[^.\n]{0,40}?"
            r"\b(?:previous|prior|above|earlier|initial|original|all|any|your|these|the)\b"
            r"[^.\n]{0,30}?\b(?:instruction|prompt|rule|direction|directive|constraint|"
            r"guardrail|guideline|restriction)s?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_disclosure",
        1.0,
        re.compile(
            r"\b(?:reveal|show|print|output|repeat|display|reproduce|disclose|"
            r"give me|tell me|what(?:'s| is| are| was| were))\b[^.\n]{0,50}?"
            r"\b(?:system (?:prompt|message|instruction)|initial prompt|"
            r"your (?:prompt|instructions|system|rules|guidelines|configuration|config)|"
            r"hidden (?:prompt|instruction|rule)|prompt above|above prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "credential_extraction",
        1.0,
        re.compile(
            r"\b(?:reveal|show|print|output|list|give|tell|dump|leak|"
            r"what(?:'s| is| are))\b[^.\n]{0,50}?"
            r"\b(?:api[ _-]?keys?|secret[ _-]?keys?|access[ _-]?tokens?|passwords?|"
            r"credentials?|connection string|database (?:url|password|credentials?)|"
            r"env(?:ironment)? (?:variable|file)s?|\.env)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "corpus_exfiltration",
        1.0,
        re.compile(
            r"\b(?:list|dump|show|print|enumerate|export|give me)\b[^.\n]{0,40}?"
            r"\b(?:all|every|each|entire|whole)\b[^.\n]{0,30}?"
            r"\b(?:documents?|files?|chunks?|passages?|collections?|embeddings?|"
            r"knowledge ?base|database|index|records?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "jailbreak_persona",
        1.0,
        re.compile(
            r"\b(?:dan mode|developer mode|jailbreak|do anything now|godmode|"
            r"unfiltered mode|no (?:restrictions|filters|rules|guardrails)|"
            r"without (?:any )?(?:restrictions|filters|censorship)|"
            r"evil (?:mode|assistant))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "delimiter_forgery",
        0.9,
        re.compile(
            r"(?:<\s*/?\s*(?:system|user_question|retrieved_evidence|instructions?|"
            r"assistant)\s*>)|(?:\[\s*(?:system|inst|/inst)\s*\])|"
            r"(?:#{2,}\s*(?:system|instruction)s?\b)|(?:\bBEGIN\s+SYSTEM\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "role_reassignment",
        0.6,
        re.compile(
            r"\b(?:you are (?:now|no longer)|from now on,? you|stop being|"
            r"pretend (?:to be|you are)|roleplay as|simulate being|"
            r"act as (?:an? )?(?:unrestricted|uncensored|different|new))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "authority_claim",
        0.5,
        re.compile(
            r"\b(?:as|i am|i'm)\s+(?:the|an?|your)\s+"
            r"(?:admin|administrator|developer|owner|engineer|operator|creator)\b"
            r"[^.\n]{0,40}?\b(?:so|now|therefore|you (?:must|should|can))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "instruction_smuggling",
        0.7,
        re.compile(
            r"(?:\bnew instructions?:)|(?:\bupdated instructions?:)|"
            r"(?:\bsystem(?: override| update):)|"
            r"(?:\bimportant: (?:you must|ignore))",
            re.IGNORECASE,
        ),
    ),
)

# A question is refused at this total. One full-weight rule reaches it; two
# half-weight suspicions do too, which is the point of adding rather than
# matching.
USER_BLOCK_THRESHOLD: Final = 1.0

# Retrieved text is held to a lower bar, because there is no cost to being
# wrong: a defanged passage still carries its facts, and a false positive costs
# a sentence its imperative mood rather than costing a visitor their answer.
EVIDENCE_FLAG_THRESHOLD: Final = 0.6

# Lines inside retrieved evidence that read as commands to the model. Matched
# per line so a document's prose survives while its injected instruction does
# not.
_EVIDENCE_IMPERATIVE = re.compile(
    r"^\s*(?:ignore|disregard|forget|override|you must|you should now|"
    r"new instructions?|system|assistant|important instruction)\b[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)

_DELIMITER_SHAPE = re.compile(
    r"<\s*/?\s*(system|user_question|retrieved_evidence|instructions?|assistant)\s*>",
    re.IGNORECASE,
)

_NEUTRALISED = "[non-instructional content removed]"


@dataclass(slots=True, frozen=True)
class InjectionVerdict:
    """What the scan found, as a score and the rule names behind it."""

    score: float
    rules: tuple[str, ...] = field(default_factory=tuple)

    @property
    def detected(self) -> bool:
        return bool(self.rules)

    @property
    def blocks_request(self) -> bool:
        return self.score >= USER_BLOCK_THRESHOLD

    @property
    def flags_evidence(self) -> bool:
        return self.score >= EVIDENCE_FLAG_THRESHOLD


def scan(text: str) -> InjectionVerdict:
    """Score a string against every rule."""
    total = 0.0
    fired: list[str] = []
    for name, weight, pattern in _RULES:
        if pattern.search(text):
            total += weight
            fired.append(name)
    return InjectionVerdict(score=round(total, 3), rules=tuple(fired))


def scan_user_input(text: str) -> InjectionVerdict:
    """The visitor's own question. A block here means no retrieval happens."""
    return scan(text)


def scan_evidence(text: str) -> InjectionVerdict:
    """A retrieved passage. Never blocks a request; decides neutralisation."""
    return scan(text)


def neutralize_evidence(text: str) -> str:
    """Strip the imperative from a passage while keeping its content.

    Two things happen. Lines that read as commands are replaced outright, and
    anything shaped like one of this service's own prompt delimiters is
    de-fanged so a passage cannot appear to end its own region and open a new
    one. The rest of the passage is untouched — a document that mentions the
    word *system* inside a sentence about a traction system keeps that sentence,
    because the rule anchors to the start of a line.
    """
    cleaned = _EVIDENCE_IMPERATIVE.sub(_NEUTRALISED, text)
    return _DELIMITER_SHAPE.sub(r"(\1)", cleaned)


def fence(tag: str, body: str) -> str:
    """Wrap a region in delimiters the body cannot close.

    The escaping is the whole point: without it, evidence containing the literal
    string ``</retrieved_evidence>`` would end the untrusted region early, and
    everything after it would read as though the system had written it.
    """
    escaped = re.sub(rf"</?\s*{re.escape(tag)}\s*>", f"({tag})", body, flags=re.IGNORECASE)
    return f"<{tag}>\n{escaped}\n</{tag}>"


__all__ = [
    "EVIDENCE_FLAG_THRESHOLD",
    "USER_BLOCK_THRESHOLD",
    "InjectionVerdict",
    "fence",
    "neutralize_evidence",
    "scan",
    "scan_evidence",
    "scan_user_input",
]
