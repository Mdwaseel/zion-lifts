"""What a page of the Zion site looks like to the assistant.

The assistant needs to answer two kinds of question about the website — "where
do I find X?" and "what does the site say about X?" — and those want different
granularity. A page answers the first; a section answers the second. So a page
carries both: a route the assistant may link to, and the sections underneath it
that the retrieval half actually matches against.

Everything here is a value object. Building an index is
:mod:`app.website.builder`'s job and searching one is :mod:`app.website.index`'s,
which keeps this module free of both the backend's JSON shape and the scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PageKind(StrEnum):
    """What sort of page this is, which decides when it is worth suggesting.

    A ``PRODUCT`` page answers "which lift", a ``NAVIGATION`` page answers
    "where do I", and a ``CONTENT`` page is neither. The distinction exists so
    that a question about contacting the company is not answered with a link to
    a blog post that happens to share vocabulary with it.
    """

    HOME = "home"
    PRODUCT = "product"
    PRODUCT_INDEX = "product_index"
    PROJECT = "project"
    PROJECT_INDEX = "project_index"
    CONTENT = "content"
    NAVIGATION = "navigation"
    JOURNAL = "journal"
    LEGAL = "legal"


@dataclass(slots=True, frozen=True)
class WebsiteSection:
    """One addressable region of a page.

    ``anchor`` is the in-page id when the section has one. It is kept separate
    from the page's route rather than pre-joined, because a link to a section
    is only offered when the anchor is known to exist — a fabricated ``#pricing``
    is exactly the sort of plausible-looking wrong answer this whole module is
    built to prevent.
    """

    name: str
    text: str = ""
    anchor: str | None = None

    def url_within(self, route: str) -> str:
        return f"{route}#{self.anchor}" if self.anchor else route


@dataclass(slots=True, frozen=True)
class WebsitePage:
    """A route on the site, with everything the assistant may say about it."""

    route: str
    title: str
    kind: PageKind = PageKind.CONTENT
    summary: str = ""
    description: str = ""
    keywords: tuple[str, ...] = field(default_factory=tuple)
    sections: tuple[WebsiteSection, ...] = field(default_factory=tuple)
    # Slugs of catalogue records this page is about. Lets a question that named
    # a product reach the product's own page rather than the index.
    product_slugs: tuple[str, ...] = field(default_factory=tuple)

    @property
    def searchable_text(self) -> str:
        """Everything about this page, as one string for lexical matching."""
        parts = [self.title, self.summary, self.description]
        parts.extend(self.keywords)
        parts.extend(s.name for s in self.sections)
        parts.extend(s.text for s in self.sections if s.text)
        return "\n".join(p for p in parts if p)

    def describe(self) -> dict[str, object]:
        """Log-safe summary: shape, not content."""
        return {
            "route": self.route,
            "kind": str(self.kind),
            "sections": len(self.sections),
        }


__all__ = ["PageKind", "WebsitePage", "WebsiteSection"]
