"""Fuse dense and lexical rankings with Reciprocal Rank Fusion.

Two retrievers with incomparable scores. Cosine similarity is bounded and
roughly calibrated between queries; a lexical score from Qdrant's IDF modifier
is neither. Adding or averaging them would mean picking a scale factor that is
wrong for most queries, so the fusion compares *ranks* instead — position one
from either retriever is worth the same, and a chunk both retrievers liked beats
a chunk only one of them found.

The RRF implementation and its tests predate Phase 4 and are unchanged. What
Phase 4 added around it: the lexical half is now scored by Qdrant rather than
rebuilt per query, and the fused set is de-duplicated by identity before it
reaches the reranker.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core import events
from app.core.constants import CANDIDATE_MULTIPLIER, DEFAULT_TOP_K, RRF_K
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.retrieval.sparse_search import SparseSearch
from app.retrieval.vector_search import VectorSearch
from app.vectorstore.base import ScoredChunk

logger = get_logger(__name__)


def chunk_identity(chunk: ScoredChunk) -> str:
    """What makes two results the same result.

    The point id, which the ingestion pipeline derives from the document version
    and the chunk index — so it is the same string whether dense or sparse
    retrieval found it, and different for the same passage in a different
    version. Falling back to the payload's ids covers a store that did not
    populate the point id.

    Deliberately not text similarity: two chunks that overlap because of the
    chunker's overlap window are genuinely two chunks, and collapsing them would
    silently narrow the context.
    """
    if chunk.id:
        return chunk.id
    meta = chunk.metadata
    version = meta.get("document_version_id", chunk.document_id)
    return f"{version}:{meta.get('chunk_index', meta.get('chunk_id', ''))}"


def deduplicate(chunks: list[ScoredChunk]) -> list[ScoredChunk]:
    """Keep the first occurrence of each chunk, preserving order.

    Order is the ranking, so first-wins keeps the better-ranked copy. Dense and
    sparse retrieval finding the same chunk is the normal case and the point of
    running both; letting it through twice would spend two of the reranker's
    slots — and two of the context budget's — on one passage.
    """
    seen: set[str] = set()
    unique: list[ScoredChunk] = []
    for chunk in chunks:
        identity = chunk_identity(chunk)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(chunk)
    return unique


def reciprocal_rank_fusion(
    rankings: list[list[ScoredChunk]],
    weights: list[float] | None = None,
    k: int = RRF_K,
) -> list[ScoredChunk]:
    """RRF compares ranks, not scores, so cosine similarity and BM25 can be
    combined without calibrating their incompatible scales."""
    weights = weights or [1.0] * len(rankings)
    fused: dict[str, ScoredChunk] = {}
    totals: dict[str, float] = {}

    for ranking, weight in zip(rankings, weights, strict=True):
        for rank, chunk in enumerate(ranking, start=1):
            identity = chunk_identity(chunk)
            totals[identity] = totals.get(identity, 0.0) + weight / (k + rank)
            fused.setdefault(identity, chunk)

    results = []
    for identity, score in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
        chunk = fused[identity]
        results.append(
            ScoredChunk(
                id=chunk.id,
                text=chunk.text,
                document_id=chunk.document_id,
                score=score,
                metadata=chunk.metadata,
            )
        )
    return results


class HybridSearch:
    """Runs both retrievers and fuses them.

    Each retriever's depth is configured rather than derived from the final
    top-k by a multiplier. The two are not the same knob: how many candidates
    the reranker should choose *between* is a recall decision, while how many
    chunks reach the model is a context-budget decision, and tying them together
    meant one could not be tuned without moving the other.
    """

    def __init__(
        self,
        vector_search: VectorSearch,
        sparse_search: SparseSearch,
        alpha: float = 0.5,
        dense_top_k: int = DEFAULT_TOP_K * CANDIDATE_MULTIPLIER**2,
        sparse_top_k: int = DEFAULT_TOP_K * CANDIDATE_MULTIPLIER**2,
        fusion_top_k: int = DEFAULT_TOP_K * CANDIDATE_MULTIPLIER,
        min_score: float = 0.0,
        rrf_k: int = RRF_K,
    ) -> None:
        self._vector = vector_search
        self._sparse = sparse_search
        self._alpha = min(max(alpha, 0.0), 1.0)
        self._dense_top_k = dense_top_k
        self._sparse_top_k = sparse_top_k
        self._fusion_top_k = fusion_top_k
        self._min_score = min_score
        self._rrf_k = rrf_k
        # Set on each search so the caller can report which halves answered.
        self.last_degradation: tuple[str, ...] = ()
        # Per-stage durations from the most recent search, in milliseconds. Held
        # here rather than returned because `search` returns chunks and every
        # caller wants those; the timings are read by the one caller that
        # reports them. Overwritten per search, so a concurrent reader could see
        # another request's numbers — acceptable for a diagnostic, and the
        # reason these are not the source for the metrics recorded below.
        self.last_timings: dict[str, float] = {}

    async def search(
        self,
        query: str,
        collection: str,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[ScoredChunk]:
        """Candidates for the reranker, best first and free of duplicates."""
        wanted = limit or self._fusion_top_k
        self.last_degradation = ()
        self.last_timings = {}

        if self._alpha >= 1.0:
            dense = await self._timed(
                "dense", self._vector.search(query, collection, self._dense_top_k, filters)
            )
            metrics.increment("retrieval_requests_total", mode="dense")
            return deduplicate(self._floor(dense))[:wanted]
        if self._alpha <= 0.0:
            sparse = await self._timed(
                "sparse", self._sparse.search(query, collection, self._sparse_top_k, filters)
            )
            metrics.increment("retrieval_requests_total", mode="sparse")
            return deduplicate(sparse)[:wanted]

        # Timed individually even though they run concurrently: the wall-clock
        # of the pair only tells you the slower one, and "which retriever is
        # slow" is the question this breakdown exists to answer.
        dense_result, sparse_result = await asyncio.gather(
            self._timed(
                "dense", self._vector.search(query, collection, self._dense_top_k, filters)
            ),
            self._timed(
                "sparse", self._sparse.search(query, collection, self._sparse_top_k, filters)
            ),
            return_exceptions=True,
        )
        dense = self._floor(self._unwrap(dense_result, "dense"))
        sparse = self._unwrap(sparse_result, "sparse")

        # One retriever failing degrades the answer; both failing means there is
        # nothing to answer from, and that must not look like an empty corpus.
        degraded = []
        if isinstance(dense_result, BaseException):
            degraded.append("dense")
        if isinstance(sparse_result, BaseException):
            degraded.append("sparse")
        self.last_degradation = tuple(degraded)

        if len(degraded) == 2:
            from app.core.errors import VectorStoreUnavailable

            raise VectorStoreUnavailable(
                "both dense and lexical retrieval failed; refusing to answer from nothing"
            )

        mark = time.perf_counter()
        fused = reciprocal_rank_fusion(
            [dense, sparse], [self._alpha, 1.0 - self._alpha], k=self._rrf_k
        )
        unique = deduplicate(fused)
        rrf_ms = (time.perf_counter() - mark) * 1000
        self.last_timings["rrf"] = rrf_ms
        metrics.observe("retrieval_stage_duration", rrf_ms, stage="rrf")

        metrics.increment("retrieval_requests_total", mode="hybrid")
        if not unique:
            # An empty result is not an error, but a rising rate of them means
            # the corpus, the filters or the embedding changed under the query.
            metrics.increment("retrieval_empty_total", mode="hybrid")

        logger.info(
            events.HYBRID_RETRIEVAL_COMPLETED,
            extra={
                "event": events.HYBRID_RETRIEVAL_COMPLETED,
                "dense_results": len(dense),
                "sparse_results": len(sparse),
                "fused_results": len(fused),
                "unique_results": len(unique),
                "returned": min(len(unique), wanted),
                "dense_ms": round(self.last_timings.get("dense", 0.0), 1),
                "sparse_ms": round(self.last_timings.get("sparse", 0.0), 1),
                "rrf_ms": round(rrf_ms, 1),
                "degraded": ",".join(degraded) or None,
            },
        )
        return unique[:wanted]

    async def _timed(self, stage: str, awaitable: Any) -> list[ScoredChunk]:
        """Run one retriever, recording how long it took either way.

        A failure is timed too. A retriever that fails after nine seconds and
        one that fails instantly are different problems — a timeout against a
        refused connection — and only the duration separates them.
        """
        mark = time.perf_counter()
        try:
            result: list[ScoredChunk] = await awaitable
        except Exception:
            took = (time.perf_counter() - mark) * 1000
            self.last_timings[stage] = took
            metrics.observe("retrieval_stage_duration", took, stage=stage, status="error")
            metrics.increment("retrieval_errors_total", stage=stage)
            raise
        took = (time.perf_counter() - mark) * 1000
        self.last_timings[stage] = took
        metrics.observe("retrieval_stage_duration", took, stage=stage, status="ok")
        logger.debug(
            events.DENSE_RETRIEVAL_COMPLETED
            if stage == "dense"
            else events.SPARSE_RETRIEVAL_COMPLETED,
            extra={"stage": stage, "results": len(result), "duration_ms": round(took, 1)},
        )
        return result

    def _floor(self, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
        """Drop dense hits below the configured similarity floor.

        Only applied to the dense ranking: cosine similarity is bounded and
        comparable between queries, so a threshold means something. Lexical
        scores are neither, and a fixed floor on them would silently empty the
        lexical half of the fusion on short queries.
        """
        if self._min_score <= 0.0:
            return chunks
        return [c for c in chunks if c.score >= self._min_score]

    @staticmethod
    def _unwrap(result: object, label: str) -> list[ScoredChunk]:
        """One retriever failing degrades the result; it must not fail the request."""
        if isinstance(result, BaseException):
            logger.warning("%s search failed", label, extra={"err": str(result)})
            return []
        return result  # type: ignore[return-value]
