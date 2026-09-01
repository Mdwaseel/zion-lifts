"""Turn an intent into a plan for where the answer may come from.

This is the whole point of routing. A single retrieval strategy applied to every
question is what produces the two failures this upgrade exists to fix: a lift
engineering question refused because it is not in the company's PDFs, and a
company claim answered from the model's own imagination because the retrieval
came back thin.

Separating the plan from both the classification and the retrieval means the
policy is one readable table. What each intent may use, whether it may speak
without evidence, and whether it may name Zion are decided here and enforced
downstream — so "never claim Zion does X without a source" is a property of one
dataclass rather than a hope about a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.query_router.intents import CONVERSATIONAL, Intent, Source
from app.website.models import PageKind

# Which classes of page each intent may be offered links to. A navigational
# question wants destinations; an engineering question wants at most a product
# page. Restricting by kind is what stops "how does traction work?" being
# answered with a link to a privacy policy that shares three words with it.
_NAV_PAGES = {
    PageKind.NAVIGATION,
    PageKind.HOME,
    PageKind.PRODUCT_INDEX,
    PageKind.PROJECT_INDEX,
    PageKind.CONTENT,
}
_PRODUCT_PAGES = {PageKind.PRODUCT, PageKind.PRODUCT_INDEX}
_ALL_PAGES = _NAV_PAGES | _PRODUCT_PAGES | {PageKind.PROJECT, PageKind.JOURNAL}


@dataclass(slots=True, frozen=True)
class SourcePlan:
    """What one question is allowed to consult, and what it may then say."""

    #: Ordered by priority. The orchestrator gathers these and no others.
    sources: tuple[Source, ...] = field(default_factory=tuple)
    #: May the model answer from its own knowledge of lift engineering?
    allow_general_knowledge: bool = False
    #: Must every company-specific claim rest on retrieved evidence?
    require_evidence_for_company_claims: bool = True
    #: Which page kinds may be suggested as links.
    page_kinds: frozenset[PageKind] = field(default_factory=lambda: frozenset(_ALL_PAGES))
    #: Upper bound on the links attached to an answer. Never more than three:
    #: a list of links is a menu, and a menu is what a visitor came here to
    #: avoid.
    max_related_pages: int = 2
    #: Skip document retrieval entirely. The fast path.
    skip_rag: bool = False

    @property
    def uses(self) -> frozenset[Source]:
        return frozenset(self.sources)

    def wants(self, source: Source) -> bool:
        return source in self.sources


# The policy table. Each row is a decision about a trade-off, and the comment on
# it is the trade-off, not a restatement of the code.
_PLANS: dict[Intent, SourcePlan] = {
    # Company facts have exactly one legitimate source each, and general
    # knowledge is not one of them: no amount of elevator expertise tells you
    # whether *this* company offers maintenance contracts.
    Intent.COMPANY_KNOWLEDGE: SourcePlan(
        sources=(Source.RAG, Source.WEBSITE),
        allow_general_knowledge=False,
        page_kinds=frozenset(_NAV_PAGES),
        max_related_pages=2,
    ),
    # Product questions are the common case and the mixed one: "which lift for a
    # villa" needs the catalogue, and "what capacity do I need" needs both the
    # catalogue and the engineering behind it. General knowledge is permitted
    # but subordinate — it may explain, it may not attribute.
    Intent.PRODUCT_INFORMATION: SourcePlan(
        sources=(Source.RAG, Source.WEBSITE, Source.GENERAL),
        allow_general_knowledge=True,
        page_kinds=frozenset(_PRODUCT_PAGES),
        max_related_pages=3,
    ),
    # A destination question. Retrieval over documents would find prose about
    # products when what was asked for was a link, so it is skipped outright —
    # this is the fast path, and it is fast because it does no vector search.
    Intent.WEBSITE_INFORMATION: SourcePlan(
        sources=(Source.WEBSITE,),
        allow_general_knowledge=False,
        page_kinds=frozenset(_ALL_PAGES),
        max_related_pages=3,
        skip_rag=True,
    ),
    # The intent this upgrade exists for. No retrieval, no refusal: an elevator
    # consultant asked how a counterweight works simply answers. The website is
    # still consulted, cheaply, so the answer can end with a relevant link when
    # one genuinely exists.
    Intent.GENERAL_LIFT_KNOWLEDGE: SourcePlan(
        sources=(Source.GENERAL, Source.WEBSITE),
        allow_general_knowledge=True,
        page_kinds=frozenset(_PRODUCT_PAGES),
        max_related_pages=1,
        skip_rag=True,
    ),
    # Both halves, and the prompt keeps them apart: the explanation is general,
    # the Zion half is evidenced, and the answer says which is which.
    Intent.MIXED_QUERY: SourcePlan(
        sources=(Source.GENERAL, Source.RAG, Source.WEBSITE),
        allow_general_knowledge=True,
        page_kinds=frozenset(_ALL_PAGES),
        max_related_pages=2,
    ),
    # Contact details are the one category where being approximately right is
    # actively harmful — a wrong phone number is worse than no phone number —
    # so this reads the website index, where the values are the site's own.
    Intent.CONTACT_OR_NAVIGATION: SourcePlan(
        sources=(Source.WEBSITE, Source.RAG),
        allow_general_knowledge=False,
        page_kinds=frozenset(_NAV_PAGES),
        max_related_pages=2,
    ),
    # Nothing is gathered. The reply is a redirect, and gathering evidence for a
    # question about cricket would only find lift documents that share a word
    # with it.
    Intent.OFF_TOPIC: SourcePlan(sources=(), allow_general_knowledge=False, skip_rag=True),
    Intent.MALICIOUS: SourcePlan(sources=(), allow_general_knowledge=False, skip_rag=True),
}

# The conversational intents all share one plan: nothing is consulted, because
# nothing was asked. "hi" has no answer to retrieve, and searching the corpus
# for it would find whichever document happens to contain the most greetings.
#
# These never reach the orchestrator in practice — the router answers them from
# written text and returns — but the table stays total over the enum so that
# `plan_for` cannot silently fall through to MIXED_QUERY and start a vector
# search for "thanks" if a future caller routes differently.
_CONVERSATIONAL_PLAN = SourcePlan(
    sources=(), allow_general_knowledge=False, max_related_pages=0, skip_rag=True
)
_PLANS.update(dict.fromkeys(CONVERSATIONAL, _CONVERSATIONAL_PLAN))


def plan_for(intent: Intent) -> SourcePlan:
    """The source plan for an intent. Total over the enum."""
    return _PLANS.get(intent, _PLANS[Intent.MIXED_QUERY])


def widen_for_low_confidence(plan: SourcePlan) -> SourcePlan:
    """Add document retrieval back to a plan that had skipped it.

    Used when the classifier was unsure and the cheap path found nothing. The
    cost is one retrieval on a question that was going to be answered badly
    otherwise; the alternative is a fast wrong answer, which is not a better
    trade at any latency.
    """
    if not plan.skip_rag and Source.RAG in plan.sources:
        return plan
    return SourcePlan(
        sources=tuple(dict.fromkeys((*plan.sources, Source.RAG))),
        allow_general_knowledge=plan.allow_general_knowledge,
        require_evidence_for_company_claims=plan.require_evidence_for_company_claims,
        page_kinds=plan.page_kinds,
        max_related_pages=plan.max_related_pages,
        skip_rag=False,
    )


__all__ = ["SourcePlan", "plan_for", "widen_for_low_confidence"]
