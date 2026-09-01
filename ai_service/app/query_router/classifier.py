"""Decide what kind of question this is, before anything expensive runs.

The classifier is deliberately rule-based and deterministic. Three reasons, in
order of how much they mattered:

*It is on the critical path of every single question.* An LLM classification is
a second round trip before retrieval has even started, on a widget where the
whole budget to first token is a second or two. Rules cost microseconds.

*Its mistakes must be inspectable.* When the assistant answers a Zion question
from general knowledge, somebody has to be able to say why. A weighted signal
list can be read; a classification from a model can only be re-run and hoped at.

*The fallback is safe.* When the rules cannot decide, the answer is not a guess —
it is :attr:`Intent.MIXED_QUERY`, which is the widest *safe* intent: it gathers
evidence, it may explain from general knowledge, and it still refuses to invent
company facts. Being unsure costs a little retrieval, never correctness.

An optional model-backed tie-breaker exists in :class:`LLMIntentClassifier` for
deployments that would rather spend the round trip on the genuinely ambiguous
minority. It is off by default and it can only *choose between* the candidates
the rules already surfaced, so enabling it cannot introduce an intent the rules
would never have considered.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Final, Protocol

from app.api.schemas.chat import Message
from app.core.logging import get_logger
from app.query_router.intents import Classification, Intent
from app.query_router.query_normalizer import NormalizedQuery

logger = get_logger(__name__)

# Words that put a question inside this assistant's world at all. Absence of
# every one of them is the strongest single signal available, and it is what
# separates "which lift for a villa" from "who won the match".
#
# Every term here is unambiguous: it belongs to lifts, to buildings, or to Zion,
# and it does not belong to anything else. The generic commercial and structural
# vocabulary that *surrounds* a lift question — price, warranty, service, floor —
# is in WEAK_DOMAIN_TERMS instead, because "what is the price of Bitcoin?" is not
# a lift question and one shared noun should not make it one.
DOMAIN_TERMS: Final[frozenset[str]] = frozenset(
    """
    lift lifts lift's elevator elevators elevator's escalator escalators
    travelator dumbwaiter dumbwaiters hoistway hoistways
    counterweight counterweights sheave sling traction hydraulic gearless geared
    mrl vvvf governor buffer interlock interlocks ard
    cabin cabins carriage
    capacity persons passengers pax headroom pit
    installation commissioning modernisation modernization retrofit
    maintenance servicing amc breakdown
    villa villas apartment apartments residential commercial
    hospital clinic warehouse penthouse duplex basement
    goods freight passenger capsule panoramic observation stacker
    stretcher wheelchair accessibility levelling leveling
    storey storeys stories
    zion zionlifts
    """.split()
)

# Vocabulary that is only a domain signal in company. A question containing
# nothing but these is not yet about lifts — but once a strong term is present,
# these are what the question is actually asking about, so they still feed the
# per-intent scoring through the phrase rules above.
WEAK_DOMAIN_TERMS: Final[frozenset[str]] = frozenset(
    """
    building buildings home homes house residence office showroom mall hotel
    factory industrial floor floors level levels stop stops door doors landing
    lobby panel car cage shaft well rope ropes drive motor brake sensor curtain
    speed load clearance overhead safety rescue overload inspection repair
    service install warranty quotation quote pricing cost price standard
    standards code codes ride platform parking
    """.split()
)

# Subjects that are unmistakably somewhere else. Only consulted when no domain
# term was found, so a question about a lift in a stadium is not thrown out for
# mentioning football.
OFF_TOPIC_TERMS: Final[frozenset[str]] = frozenset(
    """
    football cricket soccer basketball tennis match goal tournament league
    bitcoin crypto ethereum stock stocks shares nifty sensex forex trading
    weather forecast temperature rain movie film song lyrics recipe cook
    python javascript java golang rust sql regex code coding program script
    election president minister politics war vaccine covid horoscope astrology
    joke poem story essay homework translate
    """.split()
)

_WORD = re.compile(r"[a-z0-9]+")


def _rule(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# (name, intent, weight, pattern). Several may fire; the weights add. Nothing
# here matches on a single common word — every pattern is a phrase, because a
# keyword classifier on a domain this narrow decides everything by the word
# "lift".
_SIGNALS: Final[tuple[tuple[str, Intent, float, re.Pattern[str]], ...]] = (
    # --- navigation: the visitor wants a place, not a fact -------------------
    (
        "navigation_request",
        Intent.WEBSITE_INFORMATION,
        1.4,
        _rule(
            r"\b(?:where (?:can|do|would) i (?:see|find|look|read|browse)|"
            r"where (?:is|are) (?:the|your)|show me (?:the|your)|"
            r"take me to|link to|go to|navigate to|"
            r"do you have a (?:page|section)|which page|what page)\b"
        ),
    ),
    # Naming a page or a section is unambiguous: the visitor wants a
    # destination, not a description. Weighted above the product rules so that
    # "do you have a page about home lifts?" is answered with the link rather
    # than with the catalogue entry it would otherwise trigger.
    (
        "page_noun",
        Intent.WEBSITE_INFORMATION,
        2.2,
        _rule(
            r"\b(?:a|the|any|your|which|what)\s+(?:web\s?)?(?:page|section|tab|menu)\b|"
            r"\b(?:page|section)\s+(?:about|for|on)\b"
        ),
    ),
    (
        "site_vocabulary",
        Intent.WEBSITE_INFORMATION,
        1.0,
        _rule(
            r"\b(?:on your (?:website|site)|your (?:website|site|page|pages|section)|"
            r"web ?site|home ?page|catalogue|catalog|brochure|listing)\b"
        ),
    ),
    # --- contact: the visitor wants to reach a person ------------------------
    (
        "contact_request",
        Intent.CONTACT_OR_NAVIGATION,
        1.6,
        _rule(
            r"\b(?:contact (?:you|us|details|number)|get in touch|reach (?:you|out)|"
            r"phone number|your number|call you|email address|your email|"
            r"where (?:is|are) (?:your|the) (?:office|offices|showroom|branch)|"
            r"your address|visit you|book (?:a|an) (?:visit|appointment|survey)|"
            r"(?:request|get|send) (?:a|an) (?:quote|quotation|estimate|enquiry)|"
            r"speak to (?:someone|an engineer|sales))\b"
        ),
    ),
    # --- general engineering: explain a concept ------------------------------
    (
        "explanation_request",
        Intent.GENERAL_LIFT_KNOWLEDGE,
        1.3,
        _rule(
            r"\b(?:what (?:is|are|does|do)|how (?:does|do|is|are)|why (?:does|do|is|are)|"
            r"explain|describe|define|difference between|compare|"
            r"what happens (?:if|when)|what (?:if|when) .{0,20}?fails?|"
            r"what(?:'s| is) the (?:meaning|purpose|point|function)|"
            r"how (?:it|they) works?)\b"
        ),
    ),
    # "What safety devices does a lift have?" — an explanation request with a
    # noun phrase between the "what" and the verb. Two exclusions keep it
    # narrow: a product noun in the gap means a buying question rather than an
    # explanation ("what lift do I need?"), and the company as the subject of
    # the verb means a company question ("what services does Zion provide?").
    # Without the second, every direct question about Zion would be widened to
    # MIXED and would quietly regain permission to answer from general
    # knowledge — which is the one thing a company question may not do.
    (
        "explanation_request_indirect",
        Intent.GENERAL_LIFT_KNOWLEDGE,
        1.0,
        _rule(
            r"\bwhat\s+(?!lift|elevator|model|type|kind|option|product|price|cost)"
            r"(?:\w+\s+){1,3}?(?:does|do|is|are)\b"
            r"(?!\s+(?:zion|you|your|we|our|the company))"
        ),
    ),
    (
        "engineering_subject",
        Intent.GENERAL_LIFT_KNOWLEDGE,
        0.9,
        _rule(
            r"\b(?:counterweight|counter weight|traction|hydraulic|gearless|geared|"
            r"governor|buffer|safety gear|interlock|hoistway|machine room less|mrl|"
            r"vvvf|levelling|leveling|rope|sheave|duty cycle|regenerative|"
            r"door operator|landing door|car door|overspeed|rated load|"
            r"how (?:an? )?(?:lift|elevator)s? work)\b"
        ),
    ),
    # --- company: facts about Zion the organisation --------------------------
    (
        "company_subject",
        Intent.COMPANY_KNOWLEDGE,
        1.3,
        _rule(
            r"\b(?:do you (?:provide|offer|do|handle|supply|install|manufacture|make|"
            r"service|maintain|cover)|"
            r"does zion|is zion|has zion|zion(?:'s)? (?:provide|offer|do|experience|"
            r"history|team|clients?|projects?|services?|warranty|certification)|"
            r"tell me about (?:zion|your company|yourself)|about (?:your|the) company|"
            r"who are you|what do you do|how long have you|your experience|"
            r"your (?:services?|team|clients?|history|warranty|certifications?|process)|"
            r"can you (?:install|service|maintain|supply))\b"
        ),
    ),
    (
        "company_named",
        Intent.COMPANY_KNOWLEDGE,
        0.7,
        _rule(r"\bzion(?:\s+lifts?)?\b"),
    ),
    # --- product: which model, what specification ----------------------------
    (
        "product_selection",
        Intent.PRODUCT_INFORMATION,
        1.4,
        _rule(
            r"\b(?:which (?:lift|elevator|model|product|one|option)|"
            r"what (?:lift|elevator|model|type|kind|options?)|"
            r"(?:best|right|suitable|suited|recommend|recommended|ideal) "
            r"(?:for|lift|elevator|option|choice)|"
            r"suitable for|do you have (?:a|an|any)|what (?:capacit|speed|size|"
            r"dimension|specification))\w*\b"
        ),
    ),
    (
        "product_named",
        Intent.PRODUCT_INFORMATION,
        0.8,
        _rule(
            r"\b(?:passenger|home|villa|residential|hospital|stretcher|goods|freight|"
            r"service|capsule|panoramic|observation|platform|wheelchair|dumbwaiter|"
            r"dumb waiter|car stacker|parking)\s+(?:lift|elevator|stacker)s?\b"
        ),
    ),
    # --- commercial process: timelines, warranty, what a contract covers -----
    # These read like general questions ("how long does it take?") but only the
    # company can answer them, and answering from general knowledge would be an
    # invented commitment.
    (
        "company_process",
        Intent.COMPANY_KNOWLEDGE,
        1.2,
        _rule(
            r"\b(?:how long (?:does|do|will|would)[^.\n]{0,30}?"
            r"(?:take|last|install|installation|deliver|delivery)|"
            r"lead time|delivery time|installation time|turnaround|"
            r"what does (?:the |an? )?(?:amc|warranty|contract|service plan) (?:cover|include)|"
            r"warranty period|how much does[^.\n]{0,30}?cost|"
            r"what (?:is|are) (?:the |your )?(?:price|prices|pricing|cost|charges|rates))\b"
        ),
    ),
)

# A follow-up this short, containing one of these, is continuing the previous
# question rather than starting a new one — so it inherits the previous intent
# instead of being classified on words it does not contain.
_FOLLOWUP = _rule(
    r"^(?:and |but |so |also |what about |how about |ok |okay )?"
    r"(?:\w+\s+){0,6}?\b(?:it|its|it's|that|this|those|these|they|them|the same|"
    r"one|ones|instead|too|as well)\b"
)

MAX_FOLLOWUP_WORDS: Final = 10


class IntentClassifier(Protocol):
    """What the router needs from a classifier."""

    def classify(
        self, query: NormalizedQuery, history: list[Message] | None = None
    ) -> Classification: ...


class RuleIntentClassifier:
    """The default. Pure, deterministic, and about ten microseconds."""

    def classify(
        self, query: NormalizedQuery, history: list[Message] | None = None
    ) -> Classification:
        text = query.matchable
        entities = query.entities

        if not text:
            return Classification(Intent.OFF_TOPIC, 1.0, ("empty",))

        scores: dict[Intent, float] = defaultdict(float)
        signals: list[str] = []

        for name, intent, weight, pattern in _SIGNALS:
            if pattern.search(text):
                scores[intent] += weight
                signals.append(name)

        # Entity evidence, which the phrase rules cannot see: a named product
        # family is a product signal even in a sentence with no verb the rules
        # recognise ("hospital lift capacity?").
        if entities.products:
            scores[Intent.PRODUCT_INFORMATION] += 0.6
            signals.append("product_entity")
        if entities.mentions_company:
            scores[Intent.COMPANY_KNOWLEDGE] += 0.5
            signals.append("company_entity")
        if entities.floors or entities.persons or entities.weight_kg:
            scores[Intent.PRODUCT_INFORMATION] += 0.5
            signals.append("sizing_entity")

        if not self._domain_words(text):
            inherited = self._inherit(text, history)
            if inherited is not None:
                return Classification(inherited, 0.55, ("followup_inherited",))
            if self._off_topic_words(text):
                return Classification(Intent.OFF_TOPIC, 0.9, ("off_topic_subject",))
            if not scores:
                # No strong domain word and no recognised shape. Two or more of
                # the surrounding vocabulary — "what happens if the door sensor
                # fails?" — is still a lift question asked in ordinary words,
                # and calling that off topic is the failure mode that makes an
                # assistant feel obtuse. Widened rather than answered
                # confidently: MIXED gathers evidence and invents nothing.
                if len(self._weak_domain_words(text)) >= 2:
                    return Classification(Intent.MIXED_QUERY, 0.3, ("weak_domain_only",))
                return Classification(Intent.OFF_TOPIC, 0.6, ("no_domain",))

        # A question that both asks for an explanation and names the company is
        # genuinely two questions. Detected explicitly rather than left to the
        # argmax, because whichever of the two won would answer only half.
        general = scores.get(Intent.GENERAL_LIFT_KNOWLEDGE, 0.0)
        company = scores.get(Intent.COMPANY_KNOWLEDGE, 0.0) + scores.get(
            Intent.PRODUCT_INFORMATION, 0.0
        )
        # 0.8 on the company side is one named product family and nothing else —
        # "what is the capacity of passenger lifts?", where the visitor is on
        # Zion's own site asking about a range Zion sells. Explaining without
        # also checking the catalogue would answer the smaller half.
        if general >= 1.0 and company >= 0.8:
            scores[Intent.MIXED_QUERY] = general + company
            signals.append("explanation_and_company")

        # A product question that never mentions Zion is still about Zion's
        # catalogue when it asks which one to buy — the visitor is on the
        # company's own website. But a pure "what is X" is not, and the
        # explanation signal above is what tells them apart.
        if (
            scores.get(Intent.PRODUCT_INFORMATION, 0.0) > 0
            and not entities.mentions_company
            and general >= 1.3
            and company == scores.get(Intent.PRODUCT_INFORMATION, 0.0)
        ):
            scores[Intent.GENERAL_LIFT_KNOWLEDGE] += 0.4
            signals.append("unattributed_explanation")

        if not scores:
            # Domain words but no recognised shape: a lift question phrased in a
            # way the rules have never seen. Mixed gathers evidence and still
            # refuses to invent, which is the right behaviour for "don't know".
            return Classification(Intent.MIXED_QUERY, 0.35, ("domain_only",))

        ranked = sorted(scores.items(), key=lambda kv: (kv[1], kv[0].value), reverse=True)
        top_intent, top_score = ranked[0]
        total = sum(score for _, score in ranked)
        confidence = round(top_score / total, 3) if total else 0.0

        # A near-tie between two intents that want different sources is not a
        # decision worth forcing. Widening to MIXED costs one extra retrieval
        # and removes the failure where the wrong half of the question is
        # answered confidently.
        if len(ranked) > 1 and ranked[1][1] >= top_score * 0.85:
            pair = {top_intent, ranked[1][0]}
            if pair & {Intent.GENERAL_LIFT_KNOWLEDGE} and pair & {
                Intent.COMPANY_KNOWLEDGE,
                Intent.PRODUCT_INFORMATION,
            }:
                signals.append("near_tie_widened")
                return Classification(
                    Intent.MIXED_QUERY,
                    round(confidence, 3),
                    tuple(signals),
                    tuple((i, round(s, 3)) for i, s in ranked[:3]),
                )

        return Classification(
            top_intent,
            confidence,
            tuple(signals),
            tuple((i, round(s, 3)) for i, s in ranked[:3]),
        )

    @staticmethod
    def _domain_words(text: str) -> set[str]:
        return {w for w in _WORD.findall(text) if w in DOMAIN_TERMS}

    @staticmethod
    def _weak_domain_words(text: str) -> set[str]:
        return {w for w in _WORD.findall(text) if w in WEAK_DOMAIN_TERMS}

    @staticmethod
    def _off_topic_words(text: str) -> set[str]:
        return {w for w in _WORD.findall(text) if w in OFF_TOPIC_TERMS}

    @staticmethod
    def _inherit(text: str, history: list[Message] | None) -> Intent | None:
        """The previous intent, when this looks like a continuation.

        "And the capacity?" has no domain word and no shape, but it is not off
        topic — it is the second half of the question before it. Without this
        the assistant would tell a visitor mid-conversation that it only
        discusses lifts.
        """
        if not history:
            return None
        if len(_WORD.findall(text)) > MAX_FOLLOWUP_WORDS:
            return None
        if not _FOLLOWUP.search(text):
            return None
        # The previous intent is not stored on the transcript, so the best
        # available evidence is that a conversation was already in progress.
        # MIXED is the widest safe continuation.
        return Intent.MIXED_QUERY


class LLMIntentClassifier:
    """Rules first; a model only for the ambiguous remainder.

    Wraps the rule classifier rather than replacing it, and is only consulted
    when the rules were unsure. The model is given the candidates the rules
    produced and asked to choose between them — it cannot introduce a fourth
    option, so the worst case is that it agrees with the rules slowly.

    Any failure returns the rule classification unchanged. A classifier that can
    fail the request is worse than one that is occasionally wrong.
    """

    def __init__(self, llm: object, threshold: float = 0.45, enabled: bool = False) -> None:
        self._llm = llm
        self._threshold = threshold
        self._enabled = enabled
        self._rules = RuleIntentClassifier()

    def classify(
        self, query: NormalizedQuery, history: list[Message] | None = None
    ) -> Classification:
        """Synchronous path, for callers that cannot await."""
        return self._rules.classify(query, history)

    async def classify_async(
        self, query: NormalizedQuery, history: list[Message] | None = None
    ) -> Classification:
        base = self._rules.classify(query, history)
        if not self._enabled or base.confidence >= self._threshold:
            return base
        if base.intent in {Intent.OFF_TOPIC, Intent.MALICIOUS}:
            # A refusal decision is not delegated. The rules refuse on the
            # absence of evidence, and a model asked to reconsider will find a
            # reason to answer.
            return base

        candidates = [i for i, _ in base.alternatives] or [base.intent]
        try:
            chosen = await self._ask(query.original, candidates)
        except Exception as exc:
            logger.warning("intent tie-break failed", extra={"error_type": type(exc).__name__})
            return base
        if chosen is None:
            return base
        return Classification(
            chosen, max(base.confidence, 0.5), base.signals + ("llm_tiebreak",), base.alternatives
        )

    async def _ask(self, question: str, candidates: list[Intent]) -> Intent | None:
        from app.llm.base import LLMMessage

        options = ", ".join(i.value for i in candidates)
        result = await self._llm.complete(  # type: ignore[attr-defined]
            [
                LLMMessage(
                    role="system",
                    content=(
                        "Classify the user's question into exactly one of these "
                        f"categories: {options}. Reply with the category name and "
                        "nothing else."
                    ),
                ),
                LLMMessage(role="user", content=question),
            ],
            temperature=0.0,
            max_tokens=12,
        )
        answer = result.text.strip().lower()
        for candidate in candidates:
            if candidate.value in answer:
                return candidate
        return None


__all__ = [
    "DOMAIN_TERMS",
    "MAX_FOLLOWUP_WORDS",
    "OFF_TOPIC_TERMS",
    "IntentClassifier",
    "LLMIntentClassifier",
    "RuleIntentClassifier",
]
