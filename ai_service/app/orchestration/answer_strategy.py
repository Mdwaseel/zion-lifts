"""Decide how to answer, given the intent and what the evidence turned out to be.

Routing decided *where* to look. This decides what to do with what was found,
and it is the layer that replaces the old system's single behaviour — retrieve,
and refuse if the score is low. That behaviour has two failure modes and this
module exists to remove both:

*Refusing a question that needed no evidence.* "What is an MRL elevator?" has no
answer in a company's brochures and does not need one. Refusing it made the
assistant look ignorant of its own industry.

*Asking for clarification as a reflex.* A question is only ambiguous if the
answer would materially differ. "Which lift is best?" is; "what is an MRL lift?"
is not, and an assistant that asks anyway is one nobody finishes a conversation
with.

So the decision has four outcomes, and each one is reached by an explicit test
rather than by a threshold on a single number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from app.api.schemas.chat import Message
from app.core.constants import ConfidenceLevel
from app.llm.base import LLMMessage
from app.orchestration.confidence import EvidenceConfidence
from app.orchestration.evidence import EvidenceBundle, EvidenceItem
from app.prompts.assistant import system_prompt, user_prompt
from app.query_router import RouteDecision
from app.query_router.intents import ANSWERABLE_WITHOUT_EVIDENCE, Intent


class Behaviour(StrEnum):
    """What the assistant is going to do about this question."""

    #: Answer normally, using whatever the plan gathered.
    ANSWER = "answer"
    #: Answer, but told explicitly not to fill gaps with plausible specifics.
    ANSWER_LIMITED = "answer_limited"
    #: Ask one question back. Reserved for genuine ambiguity.
    CLARIFY = "clarify"
    #: A company question with nothing behind it. Say so; do not improvise.
    UNVERIFIED = "unverified"


# Superlatives and open choices with no constraint attached. These are the
# questions where an answer would be a guess about the building, not about lifts.
_OPEN_CHOICE: Final = re.compile(
    r"\b(?:which|what)\s+(?:lift|elevator|model|type|one|option|system)s?\b"
    r"[^.?\n]{0,30}?\b(?:best|right|suitable|suit|recommend|should i|do i need|"
    r"would you recommend|is good)\b"
    r"|^\s*(?:which|what)\s+(?:lift|elevator|one)\s+(?:is|would be)\s+best",
    re.IGNORECASE,
)

# Words that give a "which lift?" question enough context to be answerable —
# a building type, a use, or a constraint. Any one of these and the question is
# no longer open.
_CONTEXT_TERMS: Final[frozenset[str]] = frozenset(
    """
    home house villa apartment flat residence residential duplex penthouse
    office commercial mall hotel showroom restaurant
    hospital clinic nursing stretcher patient
    warehouse factory industrial godown goods freight cargo
    parking stacker car
    wheelchair accessibility disabled elderly
    """.split()
)

UNVERIFIED_TEMPLATE: Final = (
    "I can't confirm that from Zion's published material. Rather than guess at "
    "something specific to the company, it's worth asking the team directly — "
    "the contact page has the enquiry form and the office numbers."
)


@dataclass(slots=True, frozen=True)
class AnswerPlan:
    """A ready-to-send prompt, plus what the caller must know about it."""

    behaviour: Behaviour
    messages: list[LLMMessage] = field(default_factory=list)
    #: The evidence, in marker order, for resolving citations afterwards.
    cited_items: tuple[EvidenceItem, ...] = field(default_factory=tuple)
    #: A finished answer, when no model call is needed at all.
    fixed_text: str | None = None

    @property
    def needs_model(self) -> bool:
        return self.fixed_text is None


def is_ambiguous(decision: RouteDecision) -> bool:
    """Whether one clarifying question would change the answer materially.

    Three conditions, all required. It has to be a choice question, it has to
    name no building, use or size, and it has to be a product question — asking
    a visitor to clarify what they meant by "how does traction work" would be
    absurd. The conjunction is what keeps clarification rare.
    """
    if decision.intent is not Intent.PRODUCT_INFORMATION:
        return False
    entities = decision.query.entities
    if entities.products or entities.floors or entities.persons or entities.weight_kg:
        return False
    if any(term in _CONTEXT_TERMS for term in decision.query.matchable.split()):
        return False
    return bool(_OPEN_CHOICE.search(decision.query.matchable))


def decide(
    decision: RouteDecision, bundle: EvidenceBundle, confidence: EvidenceConfidence
) -> Behaviour:
    """Pick the behaviour. Pure, and the whole policy in one function."""
    if is_ambiguous(decision):
        return Behaviour.CLARIFY

    if decision.intent is Intent.GENERAL_LIFT_KNOWLEDGE:
        # Confidence here describes the optional supporting material, not the
        # answer. Downgrading to ANSWER_LIMITED would make the assistant hedge
        # its way through "how does a counterweight work?" because a brochure
        # happened to score poorly — which is the exact behaviour this routing
        # layer was built to remove.
        return Behaviour.ANSWER

    if bundle.is_empty:
        # No evidence. Whether that is fatal depends entirely on the intent:
        # an engineering explanation never needed any, and a company claim
        # cannot be made without it.
        if decision.plan.allow_general_knowledge and decision.intent in (
            ANSWERABLE_WITHOUT_EVIDENCE
        ):
            return Behaviour.ANSWER
        if decision.plan.allow_general_knowledge:
            return Behaviour.ANSWER_LIMITED
        return Behaviour.UNVERIFIED

    if confidence.level is ConfidenceLevel.LOW:
        # Something was found but it is weak. For a company question that is
        # not enough to make a claim on; for anything with a general half it is
        # enough to answer carefully.
        if decision.plan.allow_general_knowledge:
            return Behaviour.ANSWER_LIMITED
        return Behaviour.UNVERIFIED

    if confidence.level is ConfidenceLevel.MEDIUM:
        return Behaviour.ANSWER_LIMITED
    return Behaviour.ANSWER


def render_evidence(bundle: EvidenceBundle, max_chars: int) -> str:
    """The evidence block, numbered, labelled and budgeted.

    The budget is applied per passage in marker order and a passage that does
    not fit is dropped whole rather than truncated: half a specification is how
    a model reads "1000 kg" off a line that said "1000 kg per square metre".
    """
    blocks: list[str] = []
    budget = max_chars
    for item in bundle.items:
        block = f"[{item.marker}] {item.label}\n{item.text.strip()}"
        if len(block) > budget:
            continue
        blocks.append(block)
        budget -= len(block) + 2
    return "\n\n".join(blocks)


def render_history(history: list[Message] | None, max_turns: int = 6) -> str | None:
    if not history:
        return None
    recent = history[-max_turns:]
    return "\n".join(f"{m.role.value.capitalize()}: {m.content}" for m in recent) or None


def clarify_plan(decision: RouteDecision, history: list[Message] | None = None) -> AnswerPlan:
    """The prompt for a clarifying question, built without any evidence.

    Separate from :func:`build` so the caller can reach it *before* gathering.
    An ambiguous question is ambiguous whatever retrieval returns — "which lift
    is best?" cannot be answered by finding a better passage — so retrieving
    first would spend a vector search and a rerank on evidence that is then
    deliberately not used.
    """
    return AnswerPlan(
        behaviour=Behaviour.CLARIFY,
        messages=[
            LLMMessage(
                role="system",
                content=system_prompt(intent=str(decision.intent), clarify=True),
            ),
            LLMMessage(
                role="user",
                content=user_prompt(decision.question, "", render_history(history)),
            ),
        ],
    )


def build(
    decision: RouteDecision,
    bundle: EvidenceBundle,
    confidence: EvidenceConfidence,
    history: list[Message] | None = None,
    max_context_chars: int = 12000,
) -> AnswerPlan:
    """Turn a behaviour into the exact messages that will be sent.

    ``UNVERIFIED`` returns fixed text and no messages. There is nothing for a
    model to add to "we cannot confirm that", and asking one to phrase it is a
    round trip spent inviting it to soften the refusal into a guess.
    """
    behaviour = decide(decision, bundle, confidence)

    if behaviour is Behaviour.UNVERIFIED:
        return AnswerPlan(behaviour=behaviour, fixed_text=UNVERIFIED_TEMPLATE)

    evidence = render_evidence(bundle, max_context_chars) if bundle.items else ""
    messages = [
        LLMMessage(
            role="system",
            content=system_prompt(
                intent=str(decision.intent),
                low_evidence=behaviour is Behaviour.ANSWER_LIMITED,
                clarify=behaviour is Behaviour.CLARIFY,
            ),
        ),
        LLMMessage(
            role="user",
            content=user_prompt(decision.question, evidence, render_history(history)),
        ),
    ]
    return AnswerPlan(
        behaviour=behaviour,
        messages=messages,
        cited_items=tuple(bundle.items),
    )


__all__ = [
    "UNVERIFIED_TEMPLATE",
    "AnswerPlan",
    "Behaviour",
    "build",
    "clarify_plan",
    "decide",
    "is_ambiguous",
    "render_evidence",
    "render_history",
]
