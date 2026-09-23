"""End-to-end RAG orchestration: rewrite -> retrieve -> rerank -> generate."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol

from app.api.schemas.chat import Citation, Message
from app.core import events
from app.core.constants import CONFIDENCE_HIGH, CONFIDENCE_LOW
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.llm.base import LLMUsage
from app.prompts.system import REFUSAL_TEXT
from app.rag.answer_generator import AnswerGenerator
from app.retrieval.confidence import ConfidenceReport, assess, normalize
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.query_rewriter import QueryRewriter
from app.retrieval.scope import RetrievalScope
from app.vectorstore.base import ScoredChunk

logger = get_logger(__name__)


class Reranker(Protocol):
    async def rerank(
        self, query: str, chunks: list[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]: ...


@dataclass(slots=True)
class StageTimings:
    """Where a chat request spent its time, in milliseconds.

    Separate fields rather than a free dict because these are the ones an
    operator is asked to reason about, and a typo in a dict key produces a
    missing number rather than an error. Every field is optional: a refused
    request never reaches the model, and reporting 0.0 for a stage that did not
    run would put a misleading zero into the averages.
    """

    scope_resolution_ms: float = 0.0
    query_rewrite_ms: float = 0.0
    dense_retrieval_ms: float = 0.0
    sparse_retrieval_ms: float = 0.0
    rrf_ms: float = 0.0
    reranking_ms: float = 0.0
    grounding_ms: float = 0.0
    llm_time_to_first_token_ms: float | None = None
    llm_total_ms: float | None = None
    total_ms: float = 0.0
    # Stages that only exist on the routed path. Optional for the same reason
    # the LLM ones are: a request that skipped document retrieval did not spend
    # zero milliseconds on it, it did not run it, and the two must not average
    # together.
    routing_ms: float | None = None
    website_search_ms: float | None = None
    diversity_ms: float | None = None

    def as_log_fields(self) -> dict[str, float]:
        """Rounded, and with the stages that did not run left out."""
        fields = {
            "scope_resolution_ms": round(self.scope_resolution_ms, 1),
            "query_rewrite_ms": round(self.query_rewrite_ms, 1),
            "dense_retrieval_ms": round(self.dense_retrieval_ms, 1),
            "sparse_retrieval_ms": round(self.sparse_retrieval_ms, 1),
            "rrf_ms": round(self.rrf_ms, 1),
            "reranking_ms": round(self.reranking_ms, 1),
            "grounding_ms": round(self.grounding_ms, 1),
            "total_ms": round(self.total_ms, 1),
        }
        for name in (
            "llm_time_to_first_token_ms",
            "llm_total_ms",
            "routing_ms",
            "website_search_ms",
            "diversity_ms",
        ):
            value = getattr(self, name)
            if value is not None:
                fields[name] = round(value, 1)
        return fields


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
    timings: StageTimings = field(default_factory=StageTimings)


class RagPipeline:
    """Orchestration only. Every stage it calls is injected, and the corpus it
    reads is decided by the :class:`RetrievalScope` it is handed — never by
    anything that arrived in a request body."""

    def __init__(
        self,
        search: HybridSearch,
        reranker: Reranker,
        generator: AnswerGenerator,
        rewriter: QueryRewriter,
        embedding_model: str,
        embedding_model_version: str,
        embedding_dimension: int | None = None,
        top_k: int = 5,
        min_rerank_score: float = 0.0,
        confidence_high: float = CONFIDENCE_HIGH,
        confidence_low: float = CONFIDENCE_LOW,
        min_context_documents: int = 1,
    ) -> None:
        self._search = search
        self._reranker = reranker
        self._generator = generator
        self._rewriter = rewriter
        self._embedding_model = embedding_model
        self._embedding_model_version = embedding_model_version
        # Part of the collection name, so it has to be the dimension of the
        # provider actually in use — the same rule ingestion follows when it
        # names the collection it writes to. Omitting it here built
        # "..._v1" while ingestion had built "..._v1_d384", and every
        # knowledge-base-scoped search 404'd against a collection that had
        # never existed.
        self._embedding_dimension = embedding_dimension
        self._top_k = top_k
        self._min_rerank_score = min_rerank_score
        self._confidence_high = confidence_high
        self._confidence_low = confidence_low
        self._min_context_documents = min_context_documents

    def _assess(self, chunks: list[ScoredChunk]) -> ConfidenceReport:
        return assess(
            chunks,
            min_chunks=self._min_context_documents,
            high=self._confidence_high,
            low=self._confidence_low,
        )

    async def retrieve(
        self,
        question: str,
        scope: RetrievalScope,
        history: list[Message] | None = None,
        top_k: int | None = None,
        timings: StageTimings | None = None,
    ) -> tuple[list[ScoredChunk], str]:
        """Shared by ask() and the /search endpoint."""
        timings = timings if timings is not None else StageTimings()
        k = top_k or self._top_k

        mark = time.perf_counter()
        collection = scope.collection_for(
            self._embedding_model,
            self._embedding_model_version,
            self._embedding_dimension,
        )
        timings.scope_resolution_ms = (time.perf_counter() - mark) * 1000

        mark = time.perf_counter()
        query = await self._rewriter.rewrite(question, history or [])
        timings.query_rewrite_ms = (time.perf_counter() - mark) * 1000

        logger.info(
            events.RETRIEVAL_STARTED,
            extra={"event": events.RETRIEVAL_STARTED, "top_k": k, **scope.describe()},
        )

        try:
            candidates = await self._search.search(query, collection, scope.to_filters())
        except Exception as exc:
            metrics.increment("retrieval_errors_total", stage="search")
            logger.warning(
                events.RETRIEVAL_FAILED,
                extra={
                    "event": events.RETRIEVAL_FAILED,
                    "error_type": type(exc).__name__,
                    **scope.describe(),
                },
            )
            raise

        # Read back from the searcher rather than re-timed here: it is the only
        # place that can tell the two concurrent retrievers apart.
        stage_times = getattr(self._search, "last_timings", {}) or {}
        timings.dense_retrieval_ms = stage_times.get("dense", 0.0)
        timings.sparse_retrieval_ms = stage_times.get("sparse", 0.0)
        timings.rrf_ms = stage_times.get("rrf", 0.0)

        mark = time.perf_counter()
        chunks = await self._reranker.rerank(query, candidates, k)
        timings.reranking_ms = (time.perf_counter() - mark) * 1000
        metrics.observe("retrieval_stage_duration", timings.reranking_ms, stage="rerank")
        logger.info(
            events.RERANKING_COMPLETED,
            extra={
                "event": events.RERANKING_COMPLETED,
                "candidates": len(candidates),
                "reranked_results": len(chunks),
                "duration_ms": round(timings.reranking_ms, 1),
            },
        )

        if self._min_rerank_score > 0.0:
            # Applied after reranking rather than before: the reranker's score is
            # the only one that has looked at the query and the passage together,
            # so it is the only one worth thresholding on.
            chunks = [c for c in chunks if normalize(c.score) >= self._min_rerank_score]

        return chunks, query

    async def ask(
        self,
        question: str,
        scope: RetrievalScope,
        history: list[Message] | None = None,
        top_k: int | None = None,
    ) -> RagResult:
        started = time.perf_counter()
        timings = StageTimings()
        metrics.increment("chat_requests_total", mode="sync")

        chunks, query = await self.retrieve(question, scope, history, top_k, timings)

        mark = time.perf_counter()
        confidence = self._assess(chunks)
        timings.grounding_ms = (time.perf_counter() - mark) * 1000

        if not confidence.should_answer:
            # Refusing beats generating a confident answer from weak evidence.
            # Counted apart from an error: a refusal is the system working, and
            # a *rate* of refusals is what says the corpus has a gap.
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("grounding_refusal_total", mode="sync")
            metrics.increment("chat_refusals_total", mode="sync")
            metrics.observe("chat_duration", timings.total_ms, outcome="refused")
            logger.info(
                events.GROUNDING_REFUSED,
                extra={
                    "event": events.GROUNDING_REFUSED,
                    "score": confidence.score,
                    "reason": confidence.reason,
                    "chunks": len(chunks),
                    **scope.describe(),
                    **timings.as_log_fields(),
                },
            )
            return RagResult(
                answer=REFUSAL_TEXT,
                confidence=confidence,
                chunks=chunks,
                rewritten_query=query if query != question else None,
                took_ms=timings.total_ms,
                timings=timings,
            )

        metrics.increment("grounding_pass_total", mode="sync")
        logger.info(
            events.GROUNDING_PASSED,
            extra={
                "event": events.GROUNDING_PASSED,
                "score": confidence.score,
                "chunks": len(chunks),
            },
        )

        mark = time.perf_counter()
        try:
            generated = await self._generator.generate(question, chunks, history)
        except Exception as exc:
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("chat_errors_total", mode="sync")
            metrics.observe("chat_duration", timings.total_ms, outcome="error")
            logger.warning(
                events.CHAT_FAILED,
                extra={
                    "event": events.CHAT_FAILED,
                    "error_type": type(exc).__name__,
                    **timings.as_log_fields(),
                },
            )
            raise
        timings.llm_total_ms = (time.perf_counter() - mark) * 1000
        timings.total_ms = (time.perf_counter() - started) * 1000

        metrics.increment("chat_success_total", mode="sync")
        metrics.observe("chat_duration", timings.total_ms, outcome="answered")
        metrics.observe("llm_duration", timings.llm_total_ms, provider=generated.provider)
        metrics.increment("citations_generated_total", value=len(generated.citations))
        logger.info(
            events.CHAT_COMPLETED,
            extra={
                "event": events.CHAT_COMPLETED,
                # Counts and identifiers only — never the question, never the
                # answer, never the passages they came from.
                "chunks": len(chunks),
                "citations": len(generated.citations),
                "confidence": confidence.score,
                "provider": generated.provider,
                "model": generated.model,
                **scope.describe(),
                **timings.as_log_fields(),
            },
        )

        return RagResult(
            answer=generated.text,
            citations=generated.citations,
            confidence=confidence,
            chunks=chunks,
            rewritten_query=query if query != question else None,
            provider=generated.provider,
            model=generated.model,
            usage=generated.usage,
            took_ms=timings.total_ms,
            timings=timings,
        )

    async def ask_stream(
        self,
        question: str,
        scope: RetrievalScope,
        history: list[Message] | None = None,
        top_k: int | None = None,
    ) -> AsyncIterator[tuple[str, object]]:
        """Yield ('delta', str) events, then ('citations', list), then ('done', None).

        Time-to-first-token is measured here rather than in the route, because
        this is where the first token actually appears. It is the number that
        matters most to a reader: total duration describes a stream nobody was
        waiting on by the end, while TTFT is how long the page sat empty.
        """
        started = time.perf_counter()
        timings = StageTimings()
        metrics.increment("chat_requests_total", mode="stream")
        logger.info(events.STREAM_STARTED, extra={"event": events.STREAM_STARTED})

        chunks, _ = await self.retrieve(question, scope, history, top_k, timings)

        mark = time.perf_counter()
        confidence = self._assess(chunks)
        timings.grounding_ms = (time.perf_counter() - mark) * 1000

        if not confidence.should_answer:
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("grounding_refusal_total", mode="stream")
            metrics.increment("chat_refusals_total", mode="stream")
            metrics.observe("chat_duration", timings.total_ms, outcome="refused")
            logger.info(
                events.GROUNDING_REFUSED,
                extra={
                    "event": events.GROUNDING_REFUSED,
                    "score": confidence.score,
                    "reason": confidence.reason,
                    "chunks": len(chunks),
                    **timings.as_log_fields(),
                },
            )
            yield "delta", REFUSAL_TEXT
            yield "citations", []
            yield "done", None
            return

        metrics.increment("grounding_pass_total", mode="stream")
        collected: list[str] = []
        llm_started = time.perf_counter()

        try:
            async for event, payload in self._generator.stream(question, chunks, history):
                if event == "delta" and payload:
                    if timings.llm_time_to_first_token_ms is None:
                        timings.llm_time_to_first_token_ms = (
                            time.perf_counter() - llm_started
                        ) * 1000
                        metrics.observe(
                            "llm_time_to_first_token", timings.llm_time_to_first_token_ms
                        )
                        logger.info(
                            events.STREAM_FIRST_TOKEN,
                            extra={
                                "event": events.STREAM_FIRST_TOKEN,
                                "time_to_first_token_ms": round(
                                    timings.llm_time_to_first_token_ms, 1
                                ),
                            },
                        )
                    collected.append(payload)
                    yield "delta", payload
                elif event == "done":
                    break
        except GeneratorExit:
            # The reader went away. Not a server failure, and counted apart from
            # one: classifying a closed tab as an error would put a permanent
            # floor under the error rate that no fix could lower.
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("chat_stream_cancelled_total")
            logger.info(
                events.STREAM_CANCELLED,
                extra={
                    "event": events.STREAM_CANCELLED,
                    "delivered_chunks": len(collected),
                    **timings.as_log_fields(),
                },
            )
            raise
        except Exception as exc:
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("chat_errors_total", mode="stream")
            metrics.observe("chat_duration", timings.total_ms, outcome="error")
            logger.warning(
                events.STREAM_FAILED,
                extra={
                    "event": events.STREAM_FAILED,
                    "error_type": type(exc).__name__,
                    "delivered_chunks": len(collected),
                    **timings.as_log_fields(),
                },
            )
            raise

        timings.llm_total_ms = (time.perf_counter() - llm_started) * 1000
        timings.total_ms = (time.perf_counter() - started) * 1000
        citations = self._generator.citations_for("".join(collected), chunks)

        metrics.increment("chat_success_total", mode="stream")
        metrics.observe("chat_duration", timings.total_ms, outcome="answered")
        metrics.observe("llm_duration", timings.llm_total_ms)
        logger.info(
            events.STREAM_COMPLETED,
            extra={
                "event": events.STREAM_COMPLETED,
                "chunks": len(chunks),
                "citations": len(citations),
                "confidence": confidence.score,
                "delivered_chunks": len(collected),
                **timings.as_log_fields(),
            },
        )

        yield "citations", citations
        yield "done", None
