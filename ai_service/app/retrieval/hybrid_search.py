"""Fuse dense and lexical rankings with Reciprocal Rank Fusion."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.constants import CANDIDATE_MULTIPLIER, RRF_K
from app.core.logging import get_logger
from app.retrieval.keyword_search import KeywordSearch
from app.retrieval.vector_search import VectorSearch
from app.vectorstore.base import ScoredChunk

logger = get_logger(__name__)


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
            totals[chunk.id] = totals.get(chunk.id, 0.0) + weight / (k + rank)
            fused.setdefault(chunk.id, chunk)

    results = []
    for chunk_id, score in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
        chunk = fused[chunk_id]
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
    def __init__(
        self,
        vector_search: VectorSearch,
        keyword_search: KeywordSearch,
        alpha: float = 0.5,
        candidate_multiplier: int = CANDIDATE_MULTIPLIER,
    ) -> None:
        self._vector = vector_search
        self._keyword = keyword_search
        self._alpha = min(max(alpha, 0.0), 1.0)
        self._multiplier = candidate_multiplier

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        candidates = max(top_k * self._multiplier, top_k)

        if self._alpha >= 1.0:
            return (await self._vector.search(query, collection, candidates, filters))[:top_k]
        if self._alpha <= 0.0:
            return (await self._keyword.search(query, collection, candidates, filters))[:top_k]

        dense, sparse = await asyncio.gather(
            self._vector.search(query, collection, candidates, filters),
            self._keyword.search(query, collection, candidates, filters),
            return_exceptions=True,
        )
        dense = self._unwrap(dense, "vector")
        sparse = self._unwrap(sparse, "keyword")

        fused = reciprocal_rank_fusion([dense, sparse], [self._alpha, 1.0 - self._alpha])
        logger.debug(
            "hybrid search",
            extra={"dense": len(dense), "sparse": len(sparse), "fused": len(fused)},
        )
        return fused[:top_k]

    @staticmethod
    def _unwrap(result: object, label: str) -> list[ScoredChunk]:
        """One retriever failing degrades the result; it must not fail the request."""
        if isinstance(result, BaseException):
            logger.warning("%s search failed", label, extra={"err": str(result)})
            return []
        return result  # type: ignore[return-value]
