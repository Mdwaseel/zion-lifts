"""Embedding provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Text -> dense vector. Implementations must be safe to call concurrently."""

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages for indexing."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query (may use a different prefix/instruction)."""

    async def warmup(self) -> None:
        await self.embed_query("warmup")
