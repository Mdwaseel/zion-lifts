"""Retrieval end to end against fakes: every mode, and every boundary.

Two halves. The first checks that dense, sparse and hybrid each behave the way
their design claims — including what happens when one of them breaks. The
second is the security half, and it is written adversarially: each test tries to
reach a corpus it was not granted, using the levers a caller actually has.
"""

from __future__ import annotations

import pytest

from app.core.errors import VectorStoreUnavailable
from app.retrieval.hybrid_search import HybridSearch, deduplicate, reciprocal_rank_fusion
from app.retrieval.scope import RetrievalScope
from app.retrieval.sparse import SparseEncoder
from app.retrieval.sparse_search import SparseSearch
from app.retrieval.vector_search import VectorSearch
from app.vectorstore.base import ScoredChunk, SparseVector, VectorRecord
from app.vectorstore.collections import ACTIVE_FIELD, CollectionNameBuilder
from tests.conftest import FakeEmbeddings, InMemoryVectorStore

MODEL, VERSION, DIM = "fake", "v1", 8
KB_A, KB_B = "kb-a", "kb-b"

COLLECTION_A = CollectionNameBuilder.build(KB_A, MODEL, VERSION, DIM)
COLLECTION_B = CollectionNameBuilder.build(KB_B, MODEL, VERSION, DIM)

ENCODER = SparseEncoder()

PASSAGES = [
    ("a1", KB_A, "doc-1", "ver-1", True, "machine room less traction lift shaft width 1600 mm"),
    ("a2", KB_A, "doc-1", "ver-1", True, "hydraulic lift pit depth 1200 mm headroom 3600"),
    ("a3", KB_A, "doc-2", "ver-9", True, "annual maintenance contract covers quarterly service"),
    # A superseded edition of doc-1: present in the collection, not active.
    ("a4", KB_A, "doc-1", "ver-0", False, "machine room less traction lift shaft width 1400 mm"),
    ("b1", KB_B, "doc-9", "ver-5", True, "confidential pricing schedule for enterprise clients"),
]


async def seed() -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    embeddings = FakeEmbeddings()

    for collection in (COLLECTION_A, COLLECTION_B):
        await store.ensure_collection(collection, DIM)

    for point_id, kb, doc, version, active, text in PASSAGES:
        vector = (await embeddings.embed_documents([text]))[0]
        encoded = ENCODER.encode(text)
        await store.upsert(
            COLLECTION_A if kb == KB_A else COLLECTION_B,
            [
                VectorRecord(
                    id=point_id,
                    vector=vector,
                    text=text,
                    document_id=doc,
                    sparse=SparseVector(indices=encoded.indices, values=encoded.values),
                    metadata={
                        "knowledge_base_id": kb,
                        "document_version_id": version,
                        ACTIVE_FIELD: active,
                        "page": 1,
                        "source": f"{doc}.pdf",
                    },
                )
            ],
        )
    return store


def build_search(store, **kwargs) -> HybridSearch:
    return HybridSearch(
        vector_search=VectorSearch(FakeEmbeddings(), store),
        sparse_search=SparseSearch(store, ENCODER),
        **kwargs,
    )


def ids(chunks: list[ScoredChunk]) -> set[str]:
    return {c.id for c in chunks}


class TestRetrievalModes:
    async def test_dense_only_returns_results(self):
        store = await seed()
        search = build_search(store, alpha=1.0)
        found = await search.search("shaft width", COLLECTION_A, {"knowledge_base_id": KB_A})
        assert found

    async def test_sparse_only_returns_results(self):
        store = await seed()
        search = build_search(store, alpha=0.0)
        found = await search.search("shaft width", COLLECTION_A, {"knowledge_base_id": KB_A})
        assert found
        # Lexical retrieval is what finds an exact figure; this is the case
        # dense embeddings are worst at.
        assert "a1" in ids(found) or "a4" in ids(found)

    async def test_sparse_finds_an_exact_term_dense_may_miss(self):
        store = await seed()
        search = build_search(store, alpha=0.0)
        found = await search.search("quarterly", COLLECTION_A, {"knowledge_base_id": KB_A})
        assert "a3" in ids(found)

    async def test_hybrid_returns_the_union_of_both(self):
        store = await seed()
        hybrid = await build_search(store, alpha=0.5).search(
            "shaft width", COLLECTION_A, {"knowledge_base_id": KB_A}
        )
        dense = await build_search(store, alpha=1.0).search(
            "shaft width", COLLECTION_A, {"knowledge_base_id": KB_A}
        )
        sparse = await build_search(store, alpha=0.0).search(
            "shaft width", COLLECTION_A, {"knowledge_base_id": KB_A}
        )
        assert ids(hybrid) >= (ids(dense) | ids(sparse)) - set()

    async def test_a_query_with_no_lexical_terms_still_answers(self):
        # Every token a stopword: the sparse half contributes nothing and dense
        # carries the query alone rather than the request failing.
        store = await seed()
        found = await build_search(store, alpha=0.5).search(
            "what is the of", COLLECTION_A, {"knowledge_base_id": KB_A}
        )
        assert isinstance(found, list)

    async def test_an_empty_collection_returns_nothing_rather_than_failing(self):
        store = await seed()
        await store.ensure_collection("kb_empty__fake_v1_d8", DIM)
        found = await build_search(store, alpha=0.5).search("anything", "kb_empty__fake_v1_d8")
        assert found == []

    async def test_results_are_free_of_duplicates(self):
        store = await seed()
        found = await build_search(store, alpha=0.5).search(
            "machine room less traction lift", COLLECTION_A, {"knowledge_base_id": KB_A}
        )
        assert len(ids(found)) == len(found)

    async def test_the_fusion_depth_is_respected(self):
        store = await seed()
        found = await build_search(store, alpha=0.5, fusion_top_k=2).search(
            "lift", COLLECTION_A, {"knowledge_base_id": KB_A}
        )
        assert len(found) <= 2


class TestDegradation:
    async def test_dense_failing_leaves_sparse_answering(self):
        store = await seed()
        from tests.conftest_worker import FlakyStore

        flaky = FlakyStore(store, "search", times=99, error=VectorStoreUnavailable("dense down"))
        search = build_search(flaky, alpha=0.5)
        found = await search.search("shaft width", COLLECTION_A, {"knowledge_base_id": KB_A})

        assert found  # the lexical half carried it
        assert search.last_degradation == ("dense",)

    async def test_sparse_failing_leaves_dense_answering(self):
        store = await seed()
        from tests.conftest_worker import FlakyStore

        flaky = FlakyStore(
            store, "search_sparse", times=99, error=VectorStoreUnavailable("sparse down")
        )
        search = build_search(flaky, alpha=0.5)
        found = await search.search("shaft width", COLLECTION_A, {"knowledge_base_id": KB_A})

        assert found
        assert search.last_degradation == ("sparse",)

    async def test_both_failing_refuses_rather_than_answering_from_nothing(self):
        # An empty result here would be indistinguishable from "the corpus has
        # nothing on this", and the confidence gate would refuse politely while
        # the real problem — the store is down — went unreported.
        class DeadStore:
            async def search(self, *a, **k):
                raise VectorStoreUnavailable("down")

            async def search_sparse(self, *a, **k):
                raise VectorStoreUnavailable("down")

        search = build_search(DeadStore(), alpha=0.5)
        with pytest.raises(VectorStoreUnavailable):
            await search.search("shaft width", COLLECTION_A, {"knowledge_base_id": KB_A})


class TestActiveVersionFiltering:
    async def test_only_the_active_edition_is_searched(self):
        store = await seed()
        scope = RetrievalScope.for_knowledge_base(KB_A)
        found = await build_search(store, alpha=0.5).search(
            "machine room less traction lift shaft width",
            scope.collection_for(MODEL, VERSION, DIM),
            scope.to_filters(),
        )
        # a4 is the superseded 1400 mm edition of the same document.
        assert "a4" not in ids(found)
        assert "a1" in ids(found)

    async def test_history_can_be_reached_only_through_the_explicit_scope(self):
        store = await seed()
        scope = RetrievalScope.for_versions(KB_A, ["ver-0"])
        found = await build_search(store, alpha=0.5).search(
            "machine room less traction lift shaft width",
            scope.collection_for(MODEL, VERSION, DIM),
            scope.to_filters(),
        )
        assert ids(found) == {"a4"}

    async def test_a_processing_edition_is_invisible_until_it_is_activated(self):
        store = await seed()
        embeddings = FakeEmbeddings()
        text = "machine room less traction lift shaft width 1800 mm"
        encoded = ENCODER.encode(text)
        await store.upsert(
            COLLECTION_A,
            [
                VectorRecord(
                    id="a5",
                    vector=(await embeddings.embed_documents([text]))[0],
                    text=text,
                    document_id="doc-1",
                    sparse=SparseVector(indices=encoded.indices, values=encoded.values),
                    metadata={
                        "knowledge_base_id": KB_A,
                        "document_version_id": "ver-2",
                        ACTIVE_FIELD: False,
                    },
                )
            ],
        )

        scope = RetrievalScope.for_knowledge_base(KB_A)
        found = await build_search(store, alpha=0.5).search(
            "shaft width", scope.collection_for(MODEL, VERSION, DIM), scope.to_filters()
        )
        assert "a5" not in ids(found)

        # Activated, it takes over.
        await store.set_flag(COLLECTION_A, {"document_version_id": "ver-2"}, ACTIVE_FIELD, True)
        found = await build_search(store, alpha=0.5).search(
            "shaft width", scope.collection_for(MODEL, VERSION, DIM), scope.to_filters()
        )
        assert "a5" in ids(found)


class TestIsolation:
    """The security half. Each test is an attempt to reach KB B from KB A."""

    async def test_a_knowledge_base_scope_never_reaches_another(self):
        store = await seed()
        scope = RetrievalScope.for_knowledge_base(KB_A)
        found = await build_search(store, alpha=0.5).search(
            "confidential pricing schedule enterprise",
            scope.collection_for(MODEL, VERSION, DIM),
            scope.to_filters(),
        )
        assert "b1" not in ids(found)

    async def test_the_two_knowledge_bases_do_not_share_a_collection(self):
        # Isolation is enforced twice over: a different collection *and* a
        # filter. Either alone would be one mistake away from a leak.
        assert COLLECTION_A != COLLECTION_B

    async def test_the_filter_alone_would_also_hold(self):
        # Proven by pointing a KB A filter at KB B's collection: even with the
        # wrong collection, the payload filter refuses.
        store = await seed()
        found = await build_search(store, alpha=0.5).search(
            "confidential pricing", COLLECTION_B, {"knowledge_base_id": KB_A}
        )
        assert found == []

    async def test_a_scope_cannot_be_built_without_naming_a_knowledge_base(self):
        with pytest.raises(ValueError):
            RetrievalScope.for_knowledge_base("")

    async def test_every_knowledge_base_filter_carries_its_id(self):
        # There is no way to construct a knowledge-base scope whose filter would
        # match another corpus — including one narrowed to documents.
        for scope in (
            RetrievalScope.for_knowledge_base(KB_A),
            RetrievalScope.for_knowledge_base(KB_A, ["doc-1"]),
            RetrievalScope.for_versions(KB_A, ["ver-1"]),
        ):
            assert scope.to_filters()["knowledge_base_id"] == KB_A

    async def test_document_narrowing_cannot_widen_the_scope(self):
        store = await seed()
        scope = RetrievalScope.for_knowledge_base(KB_A, ["doc-9"])  # doc-9 lives in KB B
        found = await build_search(store, alpha=0.5).search(
            "confidential pricing",
            scope.collection_for(MODEL, VERSION, DIM),
            scope.to_filters(),
        )
        assert found == []


class TestFusion:
    def test_fusion_rewards_agreement(self):
        dense = [ScoredChunk(id="a", text="", document_id="d", score=0.0)]
        sparse = [ScoredChunk(id="a", text="", document_id="d", score=0.0)]
        fused = reciprocal_rank_fusion([dense, sparse])
        assert len(fused) == 1  # one chunk, not two

    def test_rrf_k_flattens_rank_differences(self):
        ranking = [ScoredChunk(id=str(i), text="", document_id="d", score=0.0) for i in range(5)]
        tight = reciprocal_rank_fusion([ranking], k=1)
        loose = reciprocal_rank_fusion([ranking], k=1000)
        spread_tight = tight[0].score - tight[-1].score
        spread_loose = loose[0].score - loose[-1].score
        assert spread_tight > spread_loose

    def test_deduplication_is_by_identity_not_text(self):
        # Overlapping chunks are genuinely two chunks; collapsing them on text
        # similarity would silently narrow the context.
        same_text = [
            ScoredChunk(id="a", text="identical", document_id="d", score=0.1),
            ScoredChunk(id="b", text="identical", document_id="d", score=0.1),
        ]
        assert len(deduplicate(same_text)) == 2
