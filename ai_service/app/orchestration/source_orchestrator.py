"""Gather exactly the evidence the route asked for, and nothing else.

The orchestrator is the only place that knows how to reach both corpora, and it
is deliberately thin: it does not rank, it does not decide what a question means,
and it does not write anything. It reads a :class:`~app.query_router.SourcePlan`,
runs the sources on it — concurrently, because document retrieval and website
search share nothing — sanitises what comes back, and hands over a numbered
:class:`~app.orchestration.evidence.EvidenceBundle`.

What it deliberately does *not* do is run everything and let the generator sort
it out. A general engineering question with a confident classification never
touches Qdrant; a navigational question never embeds anything. That is where the
latency saving in this upgrade actually comes from, and it only holds because
the plan is decided before any of this runs.

Document retrieval is reached through the existing :class:`RagPipeline` rather
than reimplemented. The hybrid search, the RRF and the cross-encoder are the
parts of this system that were already right, and a second retrieval path would
be a second thing to keep correct.
"""

from __future__ import annotations

import asyncio
import time
from typing import Protocol

from app.api.schemas.chat import Message
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.orchestration.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from app.query_router import RouteDecision, Source
from app.rag.pipeline import StageTimings
from app.retrieval.diversity import redundancy, select_diverse
from app.retrieval.scope import RetrievalScope
from app.security import prompt_injection
from app.vectorstore.base import ScoredChunk
from app.website.index import WebsiteIndex
from app.website.models import PageKind, WebsitePage

logger = get_logger(__name__)

#: How much of a website page may become evidence. A page summary plus its
#: matching sections; past that the page starts crowding out the documents.
MAX_PAGE_CHARS = 900

#: Website pages admitted as *evidence* (as opposed to offered as links). Kept
#: small: the page index is a navigational aid, and letting it fill the context
#: would answer product questions from marketing copy instead of datasheets.
MAX_PAGE_EVIDENCE = 2


class DocumentRetriever(Protocol):
    """The slice of :class:`~app.rag.pipeline.RagPipeline` used here."""

    async def retrieve(
        self,
        question: str,
        scope: RetrievalScope,
        history: list[Message] | None = None,
        top_k: int | None = None,
        timings: StageTimings | None = None,
    ) -> tuple[list[ScoredChunk], str]: ...


class WebsiteSource(Protocol):
    """The slice of the index provider used here."""

    @property
    def current(self) -> WebsiteIndex: ...


class SourceOrchestrator:
    """Runs the plan. One method, and everything it needs injected."""

    def __init__(
        self,
        retriever: DocumentRetriever,
        website: WebsiteSource,
        context_size: int = 5,
        diversity_lambda: float = 0.7,
    ) -> None:
        self._retriever = retriever
        self._website = website
        self._context_size = context_size
        self._lambda = diversity_lambda

    async def gather(
        self,
        decision: RouteDecision,
        scope: RetrievalScope,
        history: list[Message] | None = None,
        top_k: int | None = None,
        timings: StageTimings | None = None,
    ) -> EvidenceBundle:
        """Collect evidence for one routed question."""
        timings = timings if timings is not None else StageTimings()
        plan = decision.plan
        bundle = EvidenceBundle()

        wants_rag = plan.wants(Source.RAG) and not plan.skip_rag
        wants_web = plan.wants(Source.WEBSITE)

        if not wants_rag and not wants_web:
            return bundle

        # Independent, so concurrent. Website search is in-process and returns
        # in microseconds; running it after retrieval would add its cost to a
        # request that is already waiting on a vector store.
        chunks_task = (
            self._documents(decision, scope, history, top_k, timings) if wants_rag else _none()
        )
        pages_task = self._pages(decision, timings) if wants_web else _none()
        chunks, pages = await asyncio.gather(chunks_task, pages_task)

        empty: list[str] = []
        if wants_rag and not chunks:
            empty.append("rag")
        if wants_web and not pages:
            empty.append("website")
        bundle.empty_sources = tuple(empty)

        self._number(bundle, chunks or [], pages or [], plan.max_related_pages)
        logger.info(
            "evidence gathered",
            extra={"event": "evidence_gathered", **decision.describe(), **bundle.describe()},
        )
        return bundle

    # --- sources ----------------------------------------------------------

    async def _documents(
        self,
        decision: RouteDecision,
        scope: RetrievalScope,
        history: list[Message] | None,
        top_k: int | None,
        timings: StageTimings,
    ) -> list[ScoredChunk]:
        """Hybrid retrieval, then diversity selection over what it returned.

        The retriever is given the expanded query — the visitor's words plus the
        vocabulary this industry writes two ways — while the generator is given
        the original. Expanding for retrieval and preserving for generation is
        the whole reason those are two different strings.
        """
        wanted = top_k or self._context_size
        try:
            # Over-fetch, then let MMR choose. Asking the reranker for exactly
            # the context size would leave diversity nothing to choose between:
            # its whole job is to pick the least redundant five out of a larger
            # shortlist.
            chunks, _ = await self._retriever.retrieve(
                decision.query.retrieval, scope, history, wanted * 3, timings
            )
        except Exception as exc:
            # A failed corpus is a degraded answer, not a failed request: the
            # website half and general knowledge can still answer, and the
            # answer strategy is told there is no document evidence.
            metrics.increment("orchestrator_source_errors_total", source="rag")
            logger.warning(
                "document retrieval failed; continuing without it",
                extra={"error_type": type(exc).__name__, **decision.describe()},
            )
            return []

        if not chunks:
            return []

        mark = time.perf_counter()
        selected = select_diverse(chunks, wanted, self._lambda)
        timings.diversity_ms = (time.perf_counter() - mark) * 1000
        metrics.observe("context_redundancy", redundancy(selected) * 100)
        metrics.observe("retrieval_stage_duration", timings.diversity_ms, stage="diversity")
        return selected

    async def _pages(
        self, decision: RouteDecision, timings: StageTimings
    ) -> list[tuple[WebsitePage, str | None, float]]:
        """Search the page index. In-process, so this is a few microseconds."""
        index = self._website.current
        if index.is_empty:
            return []

        mark = time.perf_counter()
        kinds: set[PageKind] | None = set(decision.plan.page_kinds) or None
        hits = index.search(
            decision.query.retrieval,
            limit=max(decision.plan.max_related_pages, MAX_PAGE_EVIDENCE),
            kinds=kinds,
        )
        # A navigational question that matched nothing in its own class is
        # better served by the whole site than by silence — "where do I find
        # X" should reach a page even when X is on an unexpected one.
        if not hits and kinds:
            hits = index.search(decision.query.retrieval, limit=decision.plan.max_related_pages)
        timings.website_search_ms = (time.perf_counter() - mark) * 1000

        return [(hit.page, hit.section, hit.score) for hit in hits]

    # --- assembly ---------------------------------------------------------

    def _number(
        self,
        bundle: EvidenceBundle,
        chunks: list[ScoredChunk],
        pages: list[tuple[WebsitePage, str | None, float]],
        max_pages: int,
    ) -> None:
        """Assign citation markers across both kinds of evidence, once.

        Documents first, so that on a question with both, the numbering matches
        the order of authority the answer policy asks for: verified documents,
        then the website.
        """
        index = self._website.current
        marker = 0

        for chunk in chunks:
            marker += 1
            text, sanitized = _sanitize(chunk.text)
            meta = chunk.metadata
            bundle.add(
                EvidenceItem(
                    marker=marker,
                    kind=EvidenceKind.DOCUMENT,
                    title=str(meta.get("title") or meta.get("source") or chunk.document_id),
                    text=text,
                    score=float(chunk.score),
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    source=meta.get("source"),
                    sanitized=sanitized,
                )
            )
        bundle.chunks = list(chunks)

        for page, section, score in pages[:MAX_PAGE_EVIDENCE]:
            url = index.verify(page.route)
            if url is None:  # pragma: no cover - the index only holds real routes
                continue
            marker += 1
            text, sanitized = _sanitize(_page_text(page, section))
            bundle.add(
                EvidenceItem(
                    marker=marker,
                    kind=EvidenceKind.WEBSITE,
                    title=page.title,
                    text=text,
                    score=_bounded(score),
                    url=url,
                    section=section,
                    sanitized=sanitized,
                )
            )

        bundle.pages = pages[:max_pages]


#: Where a BM25 page score is worth 0.5 once bounded. Chosen from the range the
#: page index actually produces: a one-word incidental match scores around 1-2,
#: a genuine navigational match 6-15.
_PAGE_SCORE_MIDPOINT = 6.0


def _bounded(bm25: float) -> float:
    """A page score on the same 0..1 scale as a cross-encoder's.

    Necessary because confidence scoring compares the two. BM25 is unbounded and
    corpus-relative, and feeding it to the sigmoid that normalises cross-encoder
    logits would report 0.95 for any page that matched two words — an assistant
    that is highly confident about the About page because the question contained
    the word "your".
    """
    return bm25 / (bm25 + _PAGE_SCORE_MIDPOINT) if bm25 > 0 else 0.0


def _page_text(page: WebsitePage, section: str | None) -> str:
    """A page as evidence: its summary, and the section that matched.

    The matched section first when there is one — it is the part that answered
    the question, and the budget below may not reach the rest.
    """
    parts = [page.summary or page.description]
    if section:
        parts.extend(s.text for s in page.sections if s.name == section and s.text)
    parts.extend(s.text for s in page.sections if s.name != section and s.text)
    text = "\n".join(p for p in parts if p)
    return text[:MAX_PAGE_CHARS]


def _sanitize(text: str) -> tuple[str, bool]:
    """Defang a passage if it reads like an instruction, and say whether it did.

    Applied to website copy as well as to ingested documents. The site's own
    content is edited through an admin panel by people, and "people with an
    editor" is a threat model — an assistant that trusts its own CMS is one
    content edit away from being repurposed.
    """
    verdict = prompt_injection.scan_evidence(text)
    if not verdict.flags_evidence:
        return text, False
    metrics.increment("evidence_sanitized_total")
    logger.warning(
        "evidence contained instruction-like content",
        extra={"event": "evidence_sanitized", "rules": ",".join(verdict.rules)},
    )
    return prompt_injection.neutralize_evidence(text), True


async def _none() -> list:
    """An awaitable that produces nothing, so ``gather`` needs no branching."""
    return []


__all__ = [
    "MAX_PAGE_CHARS",
    "MAX_PAGE_EVIDENCE",
    "DocumentRetriever",
    "SourceOrchestrator",
    "WebsiteSource",
]
