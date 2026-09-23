"""Vector store abstraction so the RAG layer never imports a client directly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SparseVector:
    """Coordinates of a lexical vector. Empty when the text had no usable terms."""

    indices: list[int] = field(default_factory=list)
    values: list[float] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.indices


@dataclass(slots=True)
class VectorRecord:
    """A single embedded chunk ready to be persisted.

    Carries both halves of hybrid retrieval. They live on one point rather than
    in two parallel collections so that dense and sparse can never disagree
    about which chunk they are ranking, and so a delete removes both.
    """

    id: str
    vector: list[float]
    text: str
    document_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    sparse: SparseVector | None = None


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
    async def upsert(
        self, collection: str, records: list[VectorRecord], batch_size: int = 128
    ) -> int:
        """Write points, overwriting any that already exist.

        Batched because one request per vector spends an ingestion in round
        trips; upserting rather than inserting is what makes a retry safe,
        since the ids are derived from the version and the chunk index.
        """

    @abstractmethod
    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Dense nearest neighbours."""

    @abstractmethod
    async def search_sparse(
        self,
        collection: str,
        sparse: SparseVector,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Lexical matches, scored by the store rather than in this process.

        The store holds the corpus statistics that make a lexical score mean
        anything, so it is the only place the ranking can be computed without
        first reading the corpus back out.
        """

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
    async def delete_where(
        self, collection: str, filters: dict[str, Any], exclude: dict[str, Any] | None = None
    ) -> int:
        """Remove every point matching ``filters`` but not ``exclude``.

        Distinct from ``delete_document`` because deleting one *version* of a
        document must not take the edition currently answering questions with
        it — and retiring a superseded edition means "everything for this
        document except the one that just landed", which needs the exclusion.

        Deleting nothing is success, not an error: a redelivered delete message
        finds the work already done.
        """

    @abstractmethod
    async def set_flag(
        self, collection: str, filters: dict[str, Any], field: str, value: bool
    ) -> None:
        """Set one payload field on every point matching a filter.

        Server-side and one request regardless of how many points match, which
        is what makes activating a finished version cheap enough to do as a
        single step rather than as a second pass over every chunk.
        """

    @abstractmethod
    async def count(self, collection: str) -> int: ...

    @abstractmethod
    async def count_where(self, collection: str, filters: dict[str, Any]) -> int:
        """How many points match a filter. Used to verify an index is complete."""

    @abstractmethod
    async def health(self) -> bool: ...

    async def close(self) -> None:  # pragma: no cover - optional override
        return None
