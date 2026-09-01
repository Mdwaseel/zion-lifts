"""The vocabulary the router decides in.

An intent here is not a topic label. It is a *decision about where the answer
may come from*, which is why the list is short and why two questions that sound
similar can land in different intents: "what is an MRL elevator?" is answerable
from general engineering knowledge, and "does Zion build MRL elevators?" is not
answerable at all without evidence. Same subject, different intent, because the
consequence of being wrong is different.

The enum is stable API — it is returned to the client and appears in metrics —
so values are lower-case strings and are not renamed casually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Intent(StrEnum):
    """What kind of question this is, in terms of what may answer it."""

    # --- conversational -----------------------------------------------------
    # Not questions at all. They are declared before the topical intents
    # because that is the order they are tested in: a message that is purely
    # social is answered socially and never reaches retrieval. Without them the
    # only category a greeting could fall into was OFF_TOPIC, and a visitor
    # opening with "hi" was told what the assistant could not do.
    #: "hi", "hello", "good morning".
    GREETING = "greeting"
    #: "how are you?", "nice to meet you", "ok", "cool".
    SMALL_TALK = "small_talk"
    #: "thanks", "that's helpful".
    THANKS = "thanks"
    #: "bye", "see you".
    GOODBYE = "goodbye"
    #: "who are you?", "what can you do?".
    HELP = "help"

    # --- topical ------------------------------------------------------------
    #: Facts about Zion Lifts as a company: services, coverage, history, scale.
    COMPANY_KNOWLEDGE = "company_knowledge"
    #: A product question that is at least partly about Zion's own catalogue.
    PRODUCT_INFORMATION = "product_information"
    #: "Where on the site is X?" — answered from the page index.
    WEBSITE_INFORMATION = "website_information"
    #: Lift engineering that any competent elevator consultant could explain.
    GENERAL_LIFT_KNOWLEDGE = "general_lift_knowledge"
    #: Needs an explanation *and* company evidence, in one answer.
    MIXED_QUERY = "mixed_query"
    #: Contact details, offices, quotations, catalogues — a destination.
    CONTACT_OR_NAVIGATION = "contact_or_navigation"
    #: Nothing to do with lifts, Zion, or buildings.
    OFF_TOPIC = "off_topic"
    #: An attack, an abuse, or a request for a dangerous procedure.
    MALICIOUS = "malicious"


class Source(StrEnum):
    """Where evidence may be drawn from for one answer."""

    #: The ingested document corpus, through the existing RAG retrieval.
    RAG = "rag"
    #: The website page index.
    WEBSITE = "website"
    #: The model's own knowledge of lift engineering, used without evidence.
    GENERAL = "general"


#: Intents that must never produce an unsourced claim about Zion.
COMPANY_SPECIFIC: frozenset[Intent] = frozenset(
    {
        Intent.COMPANY_KNOWLEDGE,
        Intent.PRODUCT_INFORMATION,
        Intent.MIXED_QUERY,
        Intent.CONTACT_OR_NAVIGATION,
        Intent.WEBSITE_INFORMATION,
    }
)

#: Intents where refusing for lack of retrieval would be the wrong answer.
ANSWERABLE_WITHOUT_EVIDENCE: frozenset[Intent] = frozenset(
    {Intent.GENERAL_LIFT_KNOWLEDGE, Intent.MIXED_QUERY}
)

#: Social messages, answered from written text without consulting anything.
#:
#: Membership here is what exempts a message from retrieval, from the confidence
#: gate, and from being counted as a refusal — a greeting that increments the
#: refusal metric makes the number that is supposed to reveal gaps in the corpus
#: track how politely visitors open instead.
CONVERSATIONAL: frozenset[Intent] = frozenset(
    {
        Intent.GREETING,
        Intent.SMALL_TALK,
        Intent.THANKS,
        Intent.GOODBYE,
        Intent.HELP,
    }
)


@dataclass(slots=True, frozen=True)
class Classification:
    """One intent decision, with the confidence and reasons behind it.

    ``alternatives`` is kept because a near-tie is a real signal downstream: a
    question scoring almost equally as general knowledge and as a product
    question is very often genuinely both, and the orchestrator would rather
    widen its sources than pick a winner by a hair.
    """

    intent: Intent
    confidence: float
    signals: tuple[str, ...] = field(default_factory=tuple)
    alternatives: tuple[tuple[Intent, float], ...] = field(default_factory=tuple)

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.6


__all__ = [
    "ANSWERABLE_WITHOUT_EVIDENCE",
    "COMPANY_SPECIFIC",
    "CONVERSATIONAL",
    "Classification",
    "Intent",
    "Source",
]
