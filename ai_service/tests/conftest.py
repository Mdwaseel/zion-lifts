"""Shared fixtures and in-memory doubles."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.llm.base import LLMClient, LLMMessage, LLMResult, LLMUsage
from app.vectorstore.base import ScoredChunk, SparseVector, VectorRecord, VectorStore


class FakeEmbeddings:
    """Deterministic hash-based vectors: no model download in unit tests."""

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "fake"

    def _vector(self, text: str) -> list[float]:
        values = [0.0] * self._dim
        for i, char in enumerate(text.lower()):
            values[i % self._dim] += (ord(char) % 17) / 17
        norm = sum(v * v for v in values) ** 0.5 or 1.0
        return [v / norm for v in values]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self.collections: dict[str, dict[str, VectorRecord]] = {}
        # Recorded so a dimension mismatch can be exercised without a Qdrant.
        self.dimensions: dict[str, int] = {}

    async def ensure_collection(self, name: str, vector_size: int) -> None:
        self.collections.setdefault(name, {})
        self.dimensions.setdefault(name, vector_size)

    async def upsert(
        self, collection: str, records: list[VectorRecord], batch_size: int = 128
    ) -> int:
        bucket = self.collections.setdefault(collection, {})
        for record in records:
            bucket[record.id] = record
        return len(records)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))

    @staticmethod
    def _sparse_score(query: SparseVector, record: VectorRecord) -> float:
        """Dot product over shared dimensions.

        Not Qdrant's scoring — the real store applies IDF across the collection,
        which no in-memory double can reproduce faithfully. It ranks a chunk
        that shares more query terms above one that shares fewer, which is the
        property the tests around it actually depend on.
        """
        if record.sparse is None or record.sparse.is_empty:
            return 0.0
        weights = dict(zip(record.sparse.indices, record.sparse.values, strict=True))
        return sum(
            value * weights.get(index, 0.0)
            for index, value in zip(query.indices, query.values, strict=True)
        )

    async def search_sparse(
        self,
        collection: str,
        sparse: SparseVector,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        if sparse.is_empty:
            return []
        scored = [
            ScoredChunk(
                id=r.id,
                text=r.text,
                document_id=r.document_id,
                score=score,
                metadata=r.metadata,
            )
            for r in self.collections.get(collection, {}).values()
            if self._matches(r, filters) and (score := self._sparse_score(sparse, r)) > 0
        ]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _matches(record: VectorRecord, filters: dict[str, Any] | None) -> bool:
        if not filters:
            return True
        payload = {**record.metadata, "document_id": record.document_id}
        return all(payload.get(key) == value for key, value in filters.items())

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        records = [
            r for r in self.collections.get(collection, {}).values() if self._matches(r, filters)
        ]
        scored = [
            ScoredChunk(
                id=r.id,
                text=r.text,
                document_id=r.document_id,
                score=self._cosine(vector, r.vector),
                metadata=r.metadata,
            )
            for r in records
        ]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    async def scroll(
        self,
        collection: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: str | None = None,
    ) -> tuple[list[ScoredChunk], str | None]:
        records = [
            r for r in self.collections.get(collection, {}).values() if self._matches(r, filters)
        ]
        chunks = [
            ScoredChunk(
                id=r.id,
                text=r.text,
                document_id=r.document_id,
                score=0.0,
                metadata=r.metadata,
            )
            for r in records[:limit]
        ]
        return chunks, None

    async def delete_document(self, collection: str, document_id: str) -> int:
        return await self.delete_where(collection, {"document_id": document_id})

    def _select(
        self,
        collection: str,
        filters: dict[str, Any],
        exclude: dict[str, Any] | None = None,
    ) -> list[str]:
        return [
            key
            for key, record in self.collections.get(collection, {}).items()
            if self._matches(record, filters) and not (exclude and self._matches(record, exclude))
        ]

    async def delete_where(
        self, collection: str, filters: dict[str, Any], exclude: dict[str, Any] | None = None
    ) -> int:
        if not filters:
            raise ValueError("refusing to delete with an empty filter")
        bucket = self.collections.get(collection, {})
        keys = self._select(collection, filters, exclude)
        for key in keys:
            del bucket[key]
        return len(keys)

    async def set_flag(
        self, collection: str, filters: dict[str, Any], field: str, value: bool
    ) -> None:
        if not filters:
            raise ValueError("refusing to set a payload flag with an empty filter")
        bucket = self.collections.get(collection, {})
        for key in self._select(collection, filters):
            bucket[key].metadata[field] = value

    async def count(self, collection: str) -> int:
        return len(self.collections.get(collection, {}))

    async def count_where(self, collection: str, filters: dict[str, Any]) -> int:
        return len(self._select(collection, filters))

    async def collection_dimension(self, collection: str) -> int | None:
        return self.dimensions.get(collection)

    async def health(self) -> bool:
        return True


class FakeLLM(LLMClient):
    _counter = 0

    def __init__(
        self,
        reply: str = "The answer is 42 [1].",
        fail: bool = False,
        name: str | None = None,
    ) -> None:
        # Each instance needs a distinct name: FallbackLLM keys its circuit
        # breakers by provider name, so shared names would share a breaker.
        FakeLLM._counter += 1
        self.name = name or f"fake-{FakeLLM._counter}"
        self._reply = reply
        self._fail = fail
        self.calls = 0

    @property
    def model(self) -> str:
        return "fake-1"

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        self.calls += 1
        if self._fail:
            raise RuntimeError("provider down")
        return LLMResult(
            text=self._reply,
            provider=self.name,
            model=self.model,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        self.calls += 1
        if self._fail:
            raise RuntimeError("provider down")
        for word in self._reply.split(" "):
            yield word + " "


@pytest.fixture
def embeddings() -> FakeEmbeddings:
    return FakeEmbeddings()


@pytest.fixture
def store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()
