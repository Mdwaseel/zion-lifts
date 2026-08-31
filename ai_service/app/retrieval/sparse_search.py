"""Lexical retrieval, scored by Qdrant.

This replaces the previous ``KeywordSearch``, which answered every query by
scrolling up to two thousand chunks out of the store and building a BM25 index
over them in memory. That was correct and completely unscalable: the work per
query grew with the corpus, and past the scan limit recall simply stopped
improving — silently, with no error and no log line, because a truncated scan
looks exactly like a corpus with nothing better in it.

The tokenising and weighting are unchanged in spirit and live in
``app.retrieval.sparse``; what has moved is *where the corpus statistics are
computed*. Qdrant holds the collection, so Qdrant applies inverse document
frequency, and this module does nothing per query but encode the question.

Dense retrieval keeps its own module for symmetry: both are thin, both hand a
ranked list to the fusion, and neither knows the other exists.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.retrieval.sparse import SparseEncoder
from app.vectorstore.base import ScoredChunk, SparseVector, VectorStore

logger = get_logger(__name__)


class SparseSearch:
    """Encodes the query, asks the store, returns a ranked list."""

    def __init__(self, store: VectorStore, encoder: SparseEncoder | None = None) -> None:
        self._store = store
        self._encoder = encoder or SparseEncoder()

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        encoded = self._encoder.encode_query(query)
        if encoded.is_empty:
            # Every token was a stopword or a single character. There is no
            # lexical query to run, and an empty result correctly leaves the
            # dense half to answer alone.
            logger.debug("query has no lexical terms", extra={"collection": collection})
            return []

        return await self._store.search_sparse(
            collection,
            SparseVector(indices=encoded.indices, values=encoded.values),
            top_k,
            filters,
        )
