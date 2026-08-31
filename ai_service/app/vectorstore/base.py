"""Vector store abstraction so the RAG layer never imports a client directly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VectorRecord:
    """A single embedded chunk ready to be persisted."""

    id: str
    vector: list[float]
    text: str
    document_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScoredChunk:
    """A retrieval result, scored by whichever stage produced it."""

    id: str
    text: str
    document_id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Minimal contract required by retrieval and ingestion."""

    @abstractmethod
    async def ensure_collection(self, name: str, vector_size: int) -> None: ...

    @abstractmethod
    async def upsert(self, collection: str, records: list[VectorRecord]) -> int: ...

    @abstractmethod
    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]: ...

    @abstractmethod
    async def scroll(
        self,
        collection: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: str | None = None,
    ) -> tuple[list[ScoredChunk], str | None]: ...

    @abstractmethod
    async def delete_document(self, collection: str, document_id: str) -> int: ...

    @abstractmethod
    async def count(self, collection: str) -> int: ...

    @abstractmethod
    async def health(self) -> bool: ...

    async def close(self) -> None:  # pragma: no cover - optional override
        return None
