"""Sentence-Transformers embedding provider.

Encoding is CPU-bound and blocking, so every call is pushed to a worker thread
to keep the event loop responsive.
"""

from __future__ import annotations

import asyncio
from functools import partial

from app.core.logging import get_logger
from app.embeddings.cache import EmbeddingCache, cache_key
from app.embeddings.provider import EmbeddingProvider

logger = get_logger(__name__)


class HuggingFaceEmbeddings(EmbeddingProvider):
    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        batch_size: int = 32,
        cache_size: int = 4096,
        normalize: bool = True,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._normalize = normalize
        self._cache = EmbeddingCache(cache_size)
        self._model = None
        self._load_lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._model is None:
            raise RuntimeError("Model not loaded; call load() first.")
        return int(self._model.get_sentence_embedding_dimension())

    async def load(self) -> None:
        """Load weights once, off the event loop."""
        if self._model is not None:
            return
        async with self._load_lock:
            if self._model is not None:
                return
            from sentence_transformers import SentenceTransformer

            logger.info("loading embedding model", extra={"model": self._model_name})
            self._model = await asyncio.to_thread(
                SentenceTransformer, self._model_name, device=self._device
            )
            logger.info("embedding model ready", extra={"dim": self.dimension})

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(  # type: ignore[union-attr]
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=self._normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        await self.load()

        results: list[list[float] | None] = [None] * len(texts)
        pending: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            cached = self._cache.get(cache_key(self._model_name, text))
            if cached is not None:
                results[i] = cached
            else:
                pending.append((i, text))

        if pending:
            encoded = await asyncio.to_thread(
                partial(self._encode, [text for _, text in pending])
            )
            for (i, text), vector in zip(pending, encoded, strict=True):
                results[i] = vector
                self._cache.set(cache_key(self._model_name, text), vector)

        return [vector for vector in results if vector is not None]

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]

    def cache_stats(self) -> dict[str, int | float]:
        return self._cache.stats()
