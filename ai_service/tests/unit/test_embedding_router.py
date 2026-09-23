"""The embedding fallback, and the rule that keeps it from corrupting an index.

A fallback embedding model is not a fallback LLM. A different language model
gives a different answer; a different *embedding* model gives vectors in a
different geometry, and mixing them into one collection destroys retrieval
silently — nothing errors, the new chunks simply sit at meaningless distances
from every query.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.errors import EmbeddingFailed
from app.embeddings.factory import build_embeddings
from app.embeddings.router import EmbeddingRouter
from app.vectorstore.collections import CollectionNameBuilder
from tests.conftest import FakeEmbeddings

BARE = {"_env_file": None}


class NamedEmbeddings(FakeEmbeddings):
    def __init__(self, name: str, dim: int = 8, fail: bool = False) -> None:
        super().__init__(dim=dim)
        self._name = name
        self.fail = fail
        self.calls = 0

    @property
    def model_name(self) -> str:
        return self._name

    async def embed_documents(self, texts):
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self._name} unavailable")
        return await super().embed_documents(texts)

    async def embed_query(self, text):
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self._name} unavailable")
        return await super().embed_query(text)


def router(primary_fails=False, fallback=True, fallback_dim=8) -> EmbeddingRouter:
    return EmbeddingRouter(
        primary=NamedEmbeddings("primary/model", 8, fail=primary_fails),
        fallback=NamedEmbeddings("fallback/model", fallback_dim) if fallback else None,
    )


class TestDocumentEmbedding:
    async def test_the_primary_answers_when_it_can(self):
        chain = router()
        assert await chain.embed_documents(["text"])
        assert chain.model_name == "primary/model"
        assert not chain.is_degraded

    async def test_the_fallback_answers_when_the_primary_fails(self):
        chain = router(primary_fails=True)
        assert await chain.embed_documents(["text"])
        assert chain.model_name == "fallback/model"
        assert chain.is_degraded
        assert chain.fallback_events == 1

    async def test_a_failure_with_no_fallback_is_reported(self):
        chain = router(primary_fails=True, fallback=False)
        with pytest.raises(EmbeddingFailed):
            await chain.embed_documents(["text"])

    async def test_both_failing_names_both(self):
        chain = EmbeddingRouter(
            primary=NamedEmbeddings("primary/model", fail=True),
            fallback=NamedEmbeddings("fallback/model", fail=True),
        )
        with pytest.raises(EmbeddingFailed) as caught:
            await chain.embed_documents(["text"])
        assert "primary/model" in str(caught.value)
        assert "fallback/model" in str(caught.value)

    async def test_the_router_recovers_to_the_primary(self):
        # A run pinned to the fallback after one blip would keep writing to the
        # wrong collection long after the primary came back.
        primary = NamedEmbeddings("primary/model", fail=True)
        chain = EmbeddingRouter(primary=primary, fallback=NamedEmbeddings("fallback/model"))

        await chain.embed_documents(["text"])
        assert chain.is_degraded

        primary.fail = False
        await chain.embed_documents(["text"])
        assert not chain.is_degraded
        assert chain.model_name == "primary/model"

    async def test_no_texts_calls_nothing(self):
        chain = router()
        assert await chain.embed_documents([]) == []


class TestQueryEmbedding:
    async def test_a_query_never_falls_back(self):
        """The asymmetry that matters.

        A query embedded by the fallback cannot be compared with a collection
        built by the primary — the comparison is not degraded, it is
        meaningless. Failing is correct; the caller turns it into "search is
        unavailable".
        """
        fallback = NamedEmbeddings("fallback/model")
        chain = EmbeddingRouter(
            primary=NamedEmbeddings("primary/model", fail=True), fallback=fallback
        )

        with pytest.raises(EmbeddingFailed):
            await chain.embed_query("what is the shaft width?")
        assert fallback.calls == 0

    async def test_a_working_primary_embeds_queries(self):
        chain = router()
        assert len(await chain.embed_query("question")) == 8


class TestCollectionIsolation:
    async def test_fallback_vectors_are_named_for_the_fallback(self):
        """The whole point of the router.

        The pipeline names its collection from ``model_name`` *after*
        embedding, so a fallback run writes to the fallback's own collection.
        """
        chain = router(primary_fails=True)
        await chain.embed_documents(["text"])

        primary_collection = CollectionNameBuilder.build("kb-1", "primary/model", "v1", 8)
        actual = CollectionNameBuilder.build("kb-1", chain.model_name, "v1", chain.dimension)
        assert actual != primary_collection
        assert "fallback" in actual

    async def test_a_different_width_gives_a_different_collection(self):
        chain = router(primary_fails=True, fallback_dim=384)
        await chain.embed_documents(["text"])
        assert chain.dimension == 384

        name = CollectionNameBuilder.build("kb-1", chain.model_name, "v1", chain.dimension)
        assert name.endswith("_d384")
        assert name != CollectionNameBuilder.build("kb-1", "primary/model", "v1", 8)


class TestFactory:
    def test_no_fallback_configured_returns_the_bare_provider(self):
        provider = build_embeddings(Settings(**BARE))
        assert not isinstance(provider, EmbeddingRouter)

    def test_a_configured_fallback_returns_a_router(self):
        provider = build_embeddings(
            Settings(**BARE, embedding_fallback_model="BAAI/bge-small-en-v1.5")
        )
        assert isinstance(provider, EmbeddingRouter)
        assert len(provider.providers) == 2

    def test_a_fallback_identical_to_the_primary_is_ignored(self):
        # It is not a fallback; it would only fail twice as slowly.
        settings = Settings(**BARE)
        provider = build_embeddings(
            Settings(**BARE, embedding_fallback_model=settings.embedding_model)
        )
        assert not isinstance(provider, EmbeddingRouter)
