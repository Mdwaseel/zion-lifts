"""End-to-end RAG orchestration: rewrite -> retrieve -> rerank -> generate."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.api.schemas.chat import Citation, Message
from app.core.logging import get_logger
from app.llm.base import LLMUsage
from app.prompts.system import REFUSAL_TEXT
from app.rag.answer_generator import AnswerGenerator
from app.retrieval.confidence import ConfidenceReport, assess
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.query_rewriter import QueryRewriter
from app.vectorstore.base import ScoredChunk

logger = get_logger(__name__)


class Reranker(Protocol):
    async def rerank(
        self, query: str, chunks: list[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]: ...


@dataclass(slots=True)
class RagResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    confidence: ConfidenceReport | None = None
    chunks: list[ScoredChunk] = field(default_factory=list)
    rewritten_query: str | None = None
    provider: str | None = None
    model: str | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    took_ms: float = 0.0


class RagPipeline:
    def __init__(
        self,
        search: HybridSearch,
        reranker: Reranker,
        generator: AnswerGenerator,
        rewriter: QueryRewriter,
        default_collection: str,
        top_k: int = 5,
        candidate_multiplier: int = 4,
    ) -> None:
        self._search = search
        self._reranker = reranker
        self._generator = generator
        self._rewriter = rewriter
        self._default_collection = default_collection
        self._top_k = top_k
        self._multiplier = candidate_multiplier

    async def retrieve(
        self,
        question: str,
        history: list[Message] | None = None,
        collection: str | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ScoredChunk], str]:
        """Shared by ask() and the /search endpoint."""
        target = collection or self._default_collection
        k = top_k or self._top_k

        query = await self._rewriter.rewrite(question, history or [])
        candidates = await self._search.search(query, target, k * self._multiplier, filters)
        chunks = await self._reranker.rerank(query, candidates, k)
        return chunks, query

    async def ask(
        self,
        question: str,
        history: list[Message] | None = None,
        collection: str | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> RagResult:
        started = time.perf_counter()
        chunks, query = await self.retrieve(question, history, collection, top_k, filters)
        confidence = assess(chunks)

        if not confidence.should_answer:
            # Refusing beats generating a confident answer from weak evidence.
            logger.info(
                "answer withheld",
                extra={"score": confidence.score, "reason": confidence.reason},
            )
            return RagResult(
                answer=REFUSAL_TEXT,
                confidence=confidence,
                chunks=chunks,
                rewritten_query=query if query != question else None,
                took_ms=(time.perf_counter() - started) * 1000,
            )

        generated = await self._generator.generate(question, chunks, history)

        return RagResult(
            answer=generated.text,
            citations=generated.citations,
            confidence=confidence,
            chunks=chunks,
            rewritten_query=query if query != question else None,
            provider=generated.provider,
            model=generated.model,
            usage=generated.usage,
            took_ms=(time.perf_counter() - started) * 1000,
        )

    async def ask_stream(
        self,
        question: str,
        history: list[Message] | None = None,
        collection: str | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[tuple[str, object]]:
        """Yield ('delta', str) events, then ('citations', list), then ('done', None)."""
        chunks, _ = await self.retrieve(question, history, collection, top_k, filters)
        confidence = assess(chunks)

        if not confidence.should_answer:
            yield "delta", REFUSAL_TEXT
            yield "citations", []
            yield "done", None
            return

        collected: list[str] = []
        async for event, payload in self._generator.stream(question, chunks, history):
            if event == "delta" and payload:
                collected.append(payload)
                yield "delta", payload
            elif event == "done":
                break

        yield "citations", self._generator.citations_for("".join(collected), chunks)
        yield "done", None
