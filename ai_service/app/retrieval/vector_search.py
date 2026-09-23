"""Dense retrieval over the vector store."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.embeddings.provider import EmbeddingProvider
from app.vectorstore.base import ScoredChunk, VectorStore

logger = get_logger(__name__)


class VectorSearch:
    def __init__(self, embeddings: EmbeddingProvider, store: VectorStore) -> None:
        self._embeddings = embeddings
        self._store = store

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        vector = await self._embeddings.embed_query(query)
        hits = await self._store.search(collection, vector, top_k, filters)
        logger.debug("vector search", extra={"hits": len(hits), "top_k": top_k})
        return hits
