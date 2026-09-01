"""An in-memory, searchable model of the website.

Why this is not a Qdrant collection. The site is a few dozen pages, all of which
fit in a few hundred kilobytes, and the questions it answers — "where do I find
your home lifts?", "is there a contact page?" — are navigational: they are
answered by matching *names of things*, which lexical scoring does well and a
dense embedding tends to smear. Indexing it as vectors would mean an embedding
call per query, a second collection to keep in step with the document corpus,
and a rebuild on every content edit, in exchange for worse ranking on exactly
the queries it exists to serve.

So the whole index is a dict and a term table, rebuilt in one pass whenever the
content changes, and searched with BM25 — which is computable exactly here,
because unlike the chunk corpus this index holds every document it scores.

The other half of this module's job is refusal. :meth:`WebsiteIndex.verify` is
the only thing in the service permitted to say that a URL is real, and it says
so by finding the page, not by recognising the shape of the path.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from app.retrieval.sparse import tokenize
from app.website.models import PageKind, WebsitePage
from app.website.routes import route_exists

# Standard BM25 constants. k1 controls how fast term frequency saturates, b how
# strongly length is normalised. The defaults from the literature are used
# because there is nothing about a page index that argues for different ones.
_K1 = 1.2
_B = 0.75

# How much more a term is worth when it names the page rather than merely
# appearing on it.
#
# Applied as a multiplier on the term's contribution, not by repeating the term
# into the frequency counts. The difference matters more than it sounds: BM25
# saturates term frequency and then divides by document length, so a page that
# is *well described* — the products page, with a long keyword list — has its
# repetition capped and its length penalised, and ends up scoring barely above
# a page that mentions the word once in a sentence. That is how "where can I
# see your products?" comes to suggest the About page. A field multiplier is
# not saturated and not divided, so a title match stays a title match.
_STRONG_FIELD_BOOST = 2.5

# The scaffolding of a navigational question: how it is asked, not what it is
# about. Removed from the *query* only — a page that legitimately contains these
# words keeps them, but "do you have a page about home lifts?" must not reach
# the About page because it contained the word "about", or the Home page
# because it contained the word "home" in "home lifts".
_QUERY_STOPWORDS = frozenset(
    """
    about page pages section sections show see find look looking read browse
    want need get take me my your yours you can could would do does did have
    has any some please tell give link links go visit
    """.split()
)


@dataclass(slots=True, frozen=True)
class PageHit:
    """A page the query matched, and how well."""

    page: WebsitePage
    score: float
    # The section whose own text matched best, when one clearly did. Used to
    # deep-link, and left None rather than guessed when no section stands out.
    section: str | None = None


@dataclass(slots=True)
class _Entry:
    page: WebsitePage
    terms: Counter[str]
    length: int
    #: Tokens from the fields that *name* the page: its title, its keywords, its
    #: section headings, its product slugs.
    strong: frozenset[str] = frozenset()
    section_terms: tuple[tuple[str, Counter[str]], ...] = field(default_factory=tuple)


class WebsiteIndex:
    """Pages, searchable and verifiable. Immutable once built.

    Rebuilds replace the whole object rather than mutating one, so a search that
    is already running cannot see half of an update — which matters because the
    thing being updated is the set of URLs the assistant is allowed to name.
    """

    __slots__ = ("_entries", "_by_route", "_df", "_avg_length", "_slugs", "generated_at")

    def __init__(
        self,
        pages: list[WebsitePage] | tuple[WebsitePage, ...],
        generated_at: float = 0.0,
    ) -> None:
        self._entries: list[_Entry] = []
        self._by_route: dict[str, WebsitePage] = {}
        self._slugs: set[str] = set()
        self.generated_at = generated_at

        for page in pages:
            # A page whose route is not in the manifest is dropped rather than
            # indexed: it could otherwise be suggested, and the manifest is the
            # only thing standing between the assistant and an invented URL.
            slug = page.route.rsplit("/", 1)[-1]
            candidate_slugs = self._slugs | {slug}
            if not route_exists(page.route, candidate_slugs):
                continue
            if page.route in self._by_route:
                continue

            self._by_route[page.route] = page
            if page.kind in {PageKind.PRODUCT, PageKind.PROJECT, PageKind.JOURNAL}:
                self._slugs.add(slug)
            self._entries.append(self._entry_for(page))

        self._df: Counter[str] = Counter()
        for entry in self._entries:
            self._df.update(entry.terms.keys())
        total = sum(entry.length for entry in self._entries)
        self._avg_length = (total / len(self._entries)) if self._entries else 0.0

    # --- building ---------------------------------------------------------

    @staticmethod
    def _entry_for(page: WebsitePage) -> _Entry:
        terms: Counter[str] = Counter()
        strong: set[str] = set()

        def add(text: str, naming: bool = False) -> Counter[str]:
            tokens = tokenize(text)
            counted = Counter(tokens)
            terms.update(counted)
            if naming:
                strong.update(tokens)
            return counted

        add(page.title, naming=True)
        for keyword in page.keywords:
            add(keyword, naming=True)
        for slug in page.product_slugs:
            add(slug.replace("-", " "), naming=True)
        add(page.summary)
        add(page.description)

        sections: list[tuple[str, Counter[str]]] = []
        for section in page.sections:
            own = add(section.name, naming=True) + add(section.text)
            sections.append((section.name, own))

        return _Entry(
            page=page,
            terms=terms,
            length=sum(terms.values()) or 1,
            strong=frozenset(strong),
            section_terms=tuple(sections),
        )

    # --- reading ----------------------------------------------------------

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def is_empty(self) -> bool:
        return not self._entries

    @property
    def routes(self) -> frozenset[str]:
        return frozenset(self._by_route)

    @property
    def slugs(self) -> frozenset[str]:
        return frozenset(self._slugs)

    def page(self, route: str) -> WebsitePage | None:
        return self._by_route.get(route.split("#", 1)[0])

    def verify(self, url: str) -> str | None:
        """The canonical form of ``url`` if it is a real page, else ``None``.

        The single gate on every link the assistant emits. It resolves against
        the pages actually held, so a route that exists in the manifest but was
        never loaded — a product page for a lift that has been unpublished —
        fails here, which is the correct answer.

        A fragment survives only if the page declares that section; a plausible
        ``#pricing`` invented by a model is dropped and the bare route returned,
        because landing on the right page is a smaller error than landing
        nowhere.
        """
        if not url or not url.startswith("/"):
            return None
        base, _, fragment = url.partition("#")
        base = base.split("?", 1)[0].rstrip("/") or "/"

        page = self._by_route.get(base)
        if page is None:
            return None
        if not fragment:
            return base
        anchors = {s.anchor for s in page.sections if s.anchor}
        return f"{base}#{fragment}" if fragment in anchors else base

    def search(
        self, query: str, limit: int = 3, kinds: set[PageKind] | None = None
    ) -> list[PageHit]:
        """The best-matching pages for a query, strongest first.

        ``kinds`` narrows the search to a class of page. It is how a
        navigational question ("where is your office?") is kept away from a blog
        post that happens to use the same words as the contact page.
        """
        terms = [t for t in tokenize(query) if t not in _QUERY_STOPWORDS]
        if not terms or self.is_empty:
            return []

        wanted = Counter(terms)
        hits: list[PageHit] = []
        n = len(self._entries)

        for entry in self._entries:
            if kinds and entry.page.kind not in kinds:
                continue
            score = 0.0
            for term, query_count in wanted.items():
                tf = entry.terms.get(term, 0)
                if not tf:
                    continue
                df = self._df.get(term, 0)
                # BM25's IDF, in the form that stays positive for a term present
                # in most documents — a term in every page should contribute
                # almost nothing, not a negative score that penalises a match.
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                norm = (
                    tf
                    * (_K1 + 1)
                    / (tf + _K1 * (1 - _B + _B * entry.length / (self._avg_length or 1)))
                )
                boost = _STRONG_FIELD_BOOST if term in entry.strong else 1.0
                score += idf * norm * boost * min(query_count, 2)

            if score > 0:
                hits.append(PageHit(entry.page, round(score, 4), self._best_section(entry, wanted)))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    @staticmethod
    def _best_section(entry: _Entry, wanted: Counter[str]) -> str | None:
        """The section that matched, when exactly one stands out.

        Returns None on a tie or a weak match. A deep link to the wrong section
        is more annoying than a link to the page, because it scrolls the reader
        away from what they wanted.
        """
        best_name: str | None = None
        best = 0.0
        runner_up = 0.0
        for name, terms in entry.section_terms:
            overlap = float(sum(terms.get(t, 0) for t in wanted))
            if overlap > best:
                runner_up, best, best_name = best, overlap, name
            elif overlap > runner_up:
                runner_up = overlap
        if best <= 0 or best <= runner_up * 1.2:
            return None
        return best_name


EMPTY_INDEX = WebsiteIndex(())


__all__ = ["EMPTY_INDEX", "PageHit", "WebsiteIndex"]
