"""The layer that runs before retrieval, and decides whether retrieval runs.

    question
       │
       ▼  security      is this safe to act on?          security/
       ▼  normalize     what is it asking, in what words? query_normalizer.py
       ▼  converse      is this social rather than asked? conversation.py
       ▼  classify      what kind of question is it?      classifier.py
       ▼  select        what may answer it?               source_selector.py
       ▼
    RouteDecision

:class:`QueryRouter` is a pure function of its inputs and does no I/O — the
whole decision costs microseconds and can be exercised exhaustively in tests
without a model, a vector store or a network. Everything expensive happens
after it, and only for the sources it named.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.api.schemas.chat import Message
from app.core.logging import get_logger
from app.query_router.classifier import IntentClassifier, RuleIntentClassifier
from app.query_router.conversation import detect as detect_conversation
from app.query_router.intents import CONVERSATIONAL, Classification, Intent, Source
from app.query_router.query_normalizer import NormalizedQuery, normalize
from app.query_router.safety_router import SafeReply, off_topic_reply, reply_for
from app.query_router.source_selector import SourcePlan, plan_for, widen_for_low_confidence
from app.security import SecurityVerdict, ThreatKind, inspect_request

logger = get_logger(__name__)

#: Below this the classifier is treated as having guessed, and a plan that would
#: have skipped document retrieval keeps it. See
#: :func:`~app.query_router.source_selector.widen_for_low_confidence`.
LOW_CONFIDENCE: Final = 0.4


@dataclass(slots=True, frozen=True)
class RouteDecision:
    """Everything decided before any evidence is gathered."""

    query: NormalizedQuery
    intent: Intent
    plan: SourcePlan
    classification: Classification
    security: SecurityVerdict
    #: Set when the request is finished here — a refusal or a redirect. The
    #: orchestrator does nothing at all in that case.
    reply: SafeReply | None = None

    @property
    def is_terminal(self) -> bool:
        return self.reply is not None

    @property
    def is_conversational(self) -> bool:
        """A greeting or a thank-you, rather than a refusal.

        Both end the request with written text, but one is the assistant working
        and the other is it declining. The orchestrator reads this to keep them
        apart in the metrics: a refusal rate that counts greetings measures how
        politely visitors open, not where the corpus has gaps.
        """
        return self.intent in CONVERSATIONAL

    @property
    def question(self) -> str:
        """The visitor's own words, normalised but not rewritten."""
        return self.query.original

    def describe(self) -> dict[str, object]:
        """Log-safe. Names the decision and its inputs, never the question."""
        return {
            "intent": str(self.intent),
            "intent_confidence": self.classification.confidence,
            "signals": ",".join(self.classification.signals) or None,
            "sources": ",".join(s.value for s in self.plan.sources) or "none",
            "threat": str(self.security.kind) if self.security.blocked else None,
            "expansions": len(self.query.expansions) or None,
            "corrections": len(self.query.corrections) or None,
            "terminal": self.is_terminal or None,
        }


class QueryRouter:
    """Security, normalisation, classification and source selection, in order.

    The order is the design. Security runs on the raw string before anything
    parses it; normalisation happens once so every later stage sees the same
    text; classification reads the normalised form; and the source plan is a
    function of the intent alone, so it can be reasoned about without knowing
    what the classifier did to get there.
    """

    def __init__(
        self,
        classifier: IntentClassifier | None = None,
        max_question_chars: int | None = None,
    ) -> None:
        self._classifier = classifier or RuleIntentClassifier()
        self._max_chars = max_question_chars

    def route(self, question: str, history: list[Message] | None = None) -> RouteDecision:
        verdict = inspect_request(question, self._max_chars)
        query = normalize(verdict.question)

        if verdict.blocked:
            reply = reply_for(verdict.kind)
            intent = reply.intent if reply else Intent.MALICIOUS
            decision = RouteDecision(
                query=query,
                intent=intent,
                plan=plan_for(intent),
                classification=Classification(intent, 1.0, ("security",)),
                security=verdict,
                reply=reply,
            )
            logger.info("query blocked", extra={"event": "query_blocked", **decision.describe()})
            return decision

        # Social before topical. "hi" is not a question, and the classifier has
        # no rule that could see it as anything but a question with no domain
        # words in it — which is the definition of off topic, and is exactly how
        # a greeting came to be answered with a refusal.
        #
        # This runs *after* the security check, not before it as a fast path is
        # sometimes drawn. That check is a pure function costing microseconds, so
        # putting a matcher in front of it would buy nothing and would make these
        # greeting patterns the only thing between a crafted message and the rest
        # of the pipeline. Cheap is not a reason to be first.
        conversational = detect_conversation(query.matchable, has_history=bool(history))
        if conversational is not None:
            decision = RouteDecision(
                query=query,
                intent=conversational.intent,
                plan=plan_for(conversational.intent),
                classification=Classification(conversational.intent, 1.0, (conversational.signal,)),
                security=verdict,
                reply=SafeReply(
                    text=conversational.text,
                    intent=conversational.intent,
                    threat=ThreatKind.NONE,
                ),
            )
            logger.info(
                "conversational reply",
                extra={"event": "query_conversational", **decision.describe()},
            )
            return decision

        classification = self._classifier.classify(query, history)
        intent = classification.intent

        if intent is Intent.OFF_TOPIC:
            return RouteDecision(
                query=query,
                intent=intent,
                plan=plan_for(intent),
                classification=classification,
                security=verdict,
                reply=off_topic_reply(),
            )

        plan = plan_for(intent)
        if classification.confidence < LOW_CONFIDENCE:
            plan = widen_for_low_confidence(plan)

        return RouteDecision(
            query=query,
            intent=intent,
            plan=plan,
            classification=classification,
            security=verdict,
        )


__all__ = [
    "CONVERSATIONAL",
    "LOW_CONFIDENCE",
    "Classification",
    "Intent",
    "NormalizedQuery",
    "QueryRouter",
    "RouteDecision",
    "SafeReply",
    "Source",
    "SourcePlan",
    "ThreatKind",
    "normalize",
    "plan_for",
]
