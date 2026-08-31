"""Shared fixtures and in-memory doubles."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.llm.base import LLMClient, LLMMessage, LLMResult, LLMUsage
from app.vectorstore.base import ScoredChunk, VectorRecord, VectorStore


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

    async def ensure_collection(self, name: str, vector_size: int) -> None:
        self.collections.setdefault(name, {})

    async def upsert(self, collection: str, records: list[VectorRecord]) -> int:
        bucket = self.collections.setdefault(collection, {})
        for record in records:
            bucket[record.id] = record
        return len(records)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))

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
        bucket = self.collections.get(collection, {})
        ids = [k for k, v in bucket.items() if v.document_id == document_id]
        for key in ids:
            del bucket[key]
        return len(ids)

    async def count(self, collection: str) -> int:
        return len(self.collections.get(collection, {}))

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
