"""Cross-encoder reranking of retrieval candidates."""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.vectorstore.base import ScoredChunk

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Bi-encoder retrieval is recall-oriented; a cross-encoder reads the query
    and passage together and reorders the shortlist far more accurately."""

    def __init__(self, model_name: str, device: str = "cpu", batch_size: int = 16) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model = None
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        if self._model is not None:
            return
        async with self._lock:
            if self._model is not None:
                return
            from sentence_transformers import CrossEncoder

            logger.info("loading reranker", extra={"model": self._model_name})
            self._model = await asyncio.to_thread(
                CrossEncoder, self._model_name, device=self._device
            )

    def _predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        scores = self._model.predict(pairs, batch_size=self._batch_size)  # type: ignore[union-attr]
        return [float(s) for s in scores]

    async def rerank(
        self, query: str, chunks: list[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]:
        if not chunks:
            return []
        try:
            await self.load()
            scores = await asyncio.to_thread(
                self._predict, [(query, chunk.text) for chunk in chunks]
            )
        except Exception as exc:
            logger.warning("rerank failed, keeping fusion order", extra={"err": str(exc)})
            return chunks[:top_k]

        rescored = [
            ScoredChunk(
                id=chunk.id,
                text=chunk.text,
                document_id=chunk.document_id,
                score=score,
                metadata={**chunk.metadata, "retrieval_score": chunk.score},
            )
            for chunk, score in zip(chunks, scores, strict=True)
        ]
        rescored.sort(key=lambda c: c.score, reverse=True)
        return rescored[:top_k]


class NoopReranker:
    """Used when reranking is disabled, so callers need no branching."""

    async def load(self) -> None:
        return None

    async def rerank(
        self, query: str, chunks: list[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]:
        return chunks[:top_k]
