"""Everything a finished answer points at, resolved and verified.

Three kinds of reference leave this module and all three are checked rather than
generated:

*Citations* map the ``[n]`` markers the model wrote back to the passages it was
given. A marker with no passage behind it is deleted from the answer, because a
citation that resolves to nothing is worse than none — it looks like evidence.

*Related pages* are links, and links are the single easiest thing for a language
model to invent. None of these come from the model at all: they come from the
page index, and every one is passed through :meth:`WebsiteIndex.verify` on the
way out. The model never sees a URL it could copy incorrectly, so it cannot.

*Suggested questions* are follow-ups. They are composed from the route decision
and the pages actually held — never from the answer text — so they cannot
suggest asking about something that does not exist.

The restraint rule is worth stating plainly, because it is the difference
between a helpful assistant and a link farm: links are attached only when they
add a destination the answer did not already give, and never more than the
plan allows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from app.api.schemas.chat import Citation, RelatedPage
from app.orchestration.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from app.query_router import RouteDecision
from app.query_router.intents import Intent
from app.rag.citation_handler import extract_markers
from app.website.index import WebsiteIndex
from app.website.models import PageKind, WebsitePage

SNIPPET_CHARS: Final = 280

#: A page scoring below this is a word-overlap coincidence rather than a
#: destination. Suggesting it costs trust for no benefit.
MIN_PAGE_SCORE: Final = 1.2

#: A page must also reach this fraction of the best-scoring page for the query.
#: 0.75 says a second link has to be within a quarter of the best one. It is
#: deliberately blunt: a suggestion is either clearly the next place to look
#: or it is clutter, and clutter is what makes a reader stop trusting links.
RELATIVE_PAGE_FLOOR: Final = 0.75

_MARKER = re.compile(r"\[(\d{1,2})\]")


def _snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit]
    return cut[: cut.rfind(" ")].rstrip(",;:") + "…"


def strip_unresolvable_markers(answer: str, valid: set[int]) -> str:
    """Remove markers with no passage behind them, and tidy what is left."""

    def replace(match: re.Match[str]) -> str:
        return match.group(0) if int(match.group(1)) in valid else ""

    cleaned = _MARKER.sub(replace, answer)
    cleaned = re.sub(r" +([.,;:])", lambda m: m.group(1), cleaned)
    return re.sub(r"[ ]{2,}", " ", cleaned).strip()


def _citation(item: EvidenceItem) -> Citation:
    return Citation(
        marker=f"[{item.marker}]",
        type=str(item.kind),
        chunk_id=item.chunk_id or f"page:{item.url}",
        document_id=item.document_id or (item.url or ""),
        title=item.title,
        source=item.source or item.url,
        url=item.url,
        snippet=_snippet(item.text),
        score=round(float(item.score), 4),
    )


@dataclass(slots=True, frozen=True)
class ResolvedReferences:
    """The answer as it should be sent, with everything attached to it."""

    answer: str
    citations: list[Citation]
    related_pages: list[RelatedPage]
    suggested_questions: list[str]

    @property
    def cited_count(self) -> int:
        return len(self.citations)


def build_citations(answer: str, items: tuple[EvidenceItem, ...]) -> tuple[str, list[Citation]]:
    """Resolve the markers in an answer. Returns the cleaned answer and its sources.

    Only the passages actually cited are returned, in the order they were cited.
    Deliberately no fallback to "here are the passages it saw": on this
    assistant an uncited answer is usually a general-knowledge answer, and
    attaching sources to it would assert a grounding that is not there — which
    is the exact failure the attribution rule exists to prevent.
    """
    by_marker = {item.marker: item for item in items}
    used = [n for n in extract_markers(answer) if n in by_marker]
    cleaned = strip_unresolvable_markers(answer, set(used))
    return cleaned, [_citation(by_marker[n]) for n in used]


def _page_link(page: WebsitePage, section: str | None, index: WebsiteIndex) -> RelatedPage | None:
    """A link, or nothing. The one place a URL becomes visible to a client."""
    target = page.route
    if section:
        anchor = next((s.anchor for s in page.sections if s.name == section and s.anchor), None)
        if anchor:
            target = f"{page.route}#{anchor}"
    verified = index.verify(target)
    if verified is None:
        return None
    return RelatedPage(
        title=page.title,
        url=verified,
        section=section,
        description=page.summary or page.description or None,
    )


def build_related_pages(
    decision: RouteDecision,
    bundle: EvidenceBundle,
    index: WebsiteIndex,
    citations: list[Citation],
) -> list[RelatedPage]:
    """The links worth showing, verified, deduplicated and capped.

    A page already cited in the answer is skipped: the visitor has the link in
    the source list, and repeating it below is the sort of duplication that
    makes a good suggestion look like clutter.
    """
    limit = decision.plan.max_related_pages
    if limit <= 0 or not bundle.pages:
        return []

    cited_urls = {c.url for c in citations if c.url}

    # Everything that could be offered, before any scoring decision. The home
    # page is dropped here rather than skipped in the loop below: the visitor is
    # already on the site, so "go to the home page" is never the useful half of
    # an answer — and because it is also the page most likely to top the ranking
    # on a word like "home", leaving it in would set the relative floor from a
    # page nobody was going to be shown.
    candidates = [
        (page, section, score)
        for page, section, score in bundle.pages
        if page.kind is not PageKind.HOME
    ]
    if not candidates:
        return []

    # Relative as well as absolute. A page scoring a fraction of the best match
    # is a coincidence of shared words — it is how "where can I see your
    # products?" ends up suggesting the About page, which does contain the word
    # — and the absolute floor alone cannot catch it, because BM25 scores are
    # not comparable between queries.
    best = max(score for _, _, score in candidates)
    floor = max(MIN_PAGE_SCORE, best * RELATIVE_PAGE_FLOOR)

    links: list[RelatedPage] = []
    seen: set[str] = set()
    for page, section, score in candidates:
        if score < floor:
            continue
        link = _page_link(page, section, index)
        if link is None or link.url in seen or link.url in cited_urls:
            continue
        seen.add(link.url)
        links.append(link)
        if len(links) >= limit:
            break

    return links


# Follow-ups per intent, phrased as a visitor would ask them. Fixed text, so
# nothing here can suggest a product or a page that does not exist.
_SUGGESTIONS: Final[dict[Intent, tuple[str, ...]]] = {
    Intent.GENERAL_LIFT_KNOWLEDGE: (
        "Which lift type suits a four-storey home?",
        "What shaft size does that need?",
    ),
    Intent.PRODUCT_INFORMATION: (
        "What pit depth and headroom does that need?",
        "How long does installation usually take?",
    ),
    Intent.COMPANY_KNOWLEDGE: (
        "What does an annual maintenance contract cover?",
        "Which projects has Zion completed recently?",
    ),
    Intent.MIXED_QUERY: (
        "What capacity would you recommend?",
        "How does the maintenance schedule work?",
    ),
    Intent.WEBSITE_INFORMATION: (
        "Which lift suits a residential building?",
        "How do I request a quotation?",
    ),
    Intent.CONTACT_OR_NAVIGATION: (
        "What information do you need for a quotation?",
        "Do you handle maintenance for existing lifts?",
    ),
}

MAX_SUGGESTIONS: Final = 2


def build_suggestions(decision: RouteDecision) -> list[str]:
    """Two follow-ups, or none for a refusal.

    None after a refusal or a redirect on purpose: offering a menu of questions
    to somebody who has just been told no reads as deflection, and offering one
    after a jailbreak attempt is an invitation to keep going.
    """
    if decision.is_terminal:
        return []
    return list(_SUGGESTIONS.get(decision.intent, ())[:MAX_SUGGESTIONS])


def resolve(
    answer: str,
    decision: RouteDecision,
    bundle: EvidenceBundle,
    items: tuple[EvidenceItem, ...],
    index: WebsiteIndex,
) -> ResolvedReferences:
    """Everything attached to one finished answer, in one call."""
    cleaned, citations = build_citations(answer, items)
    return ResolvedReferences(
        answer=cleaned,
        citations=citations,
        related_pages=build_related_pages(decision, bundle, index, citations),
        suggested_questions=build_suggestions(decision),
    )


__all__ = [
    "MAX_SUGGESTIONS",
    "MIN_PAGE_SCORE",
    "RELATIVE_PAGE_FLOOR",
    "SNIPPET_CHARS",
    "EvidenceKind",
    "PageKind",
    "ResolvedReferences",
    "build_citations",
    "build_related_pages",
    "build_suggestions",
    "resolve",
    "strip_unresolvable_markers",
]
