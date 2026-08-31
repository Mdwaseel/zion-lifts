"""Hybrid retrieval against a real Qdrant.

Everything else in the suite runs against an in-memory double, which is fast and
which cannot tell us the one thing that matters here: whether the sparse-vector
API is used correctly. Named vectors, the IDF modifier, sparse queries and
filtered deletion are all Qdrant behaviour, and a double that reimplements them
is a double that agrees with whatever the implementation happens to do.

Skipped unless a Qdrant is reachable::

    docker run -d -p 6333:6333 qdrant/qdrant:v1.12.4
    QDRANT_TEST_URL=http://localhost:6333 pytest -m integration

Each test builds its own collection under a random name and drops it afterwards,
so a shared cluster is safe and a failed run leaves nothing behind.
"""

from __future__ import annotations

import os
import uuid

import pytest

from app.retrieval.sparse import SparseEncoder
from app.vectorstore.base import SparseVector, VectorRecord
from app.vectorstore.collections import ACTIVE_FIELD
from app.vectorstore.qdrant import QdrantVectorStore

pytestmark = pytest.mark.integration

QDRANT_URL = os.getenv("QDRANT_TEST_URL", "")

requires_qdrant = pytest.mark.skipif(
    not QDRANT_URL,
    reason="set QDRANT_TEST_URL to a running Qdrant to exercise the real store",
)

DIM = 8
ENCODER = SparseEncoder()

# Deliberately chosen so the two halves of retrieval disagree: the lexical query
# below contains a rare exact token that only one passage has.
PASSAGES = [
    ("p1", "doc-1", "ver-1", True, "machine room less traction lift shaft width 1600 mm"),
    ("p2", "doc-1", "ver-1", True, "hydraulic lift pit depth 1200 mm and headroom 3600 mm"),
    ("p3", "doc-2", "ver-2", True, "annual maintenance contract covers quarterly servicing"),
    ("p4", "doc-1", "ver-0", False, "superseded shaft width 1400 mm from the previous edition"),
]


def fake_vector(seed: str) -> list[float]:
    """A deterministic unit-ish vector. The dense half is not what is under
    test here; the store's handling of it is."""
    values = [0.0] * DIM
    for i, char in enumerate(seed):
        values[i % DIM] += (ord(char) % 17) / 17
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values]


@pytest.fixture
async def store():
    client = QdrantVectorStore(url=QDRANT_URL, timeout=15.0)
    yield client
    await client.close()


@pytest.fixture
async def collection(store):
    name = f"zion_test_{uuid.uuid4().hex[:10]}"
    await store.ensure_collection(name, DIM)

    records = []
    for point_id, doc, version, active, text in PASSAGES:
        encoded = ENCODER.encode(text)
        records.append(
            VectorRecord(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, point_id)),
                vector=fake_vector(text),
                text=text,
                document_id=doc,
                sparse=SparseVector(indices=encoded.indices, values=encoded.values),
                metadata={
                    "knowledge_base_id": "kb-test",
                    "document_version_id": version,
                    ACTIVE_FIELD: active,
                    "page": 1,
                    "source": f"{doc}.pdf",
                    "point_ref": point_id,
                },
            )
        )
    await store.upsert(name, records, batch_size=2)

    yield name

    await store._client.delete_collection(name)  # noqa: SLF001 - test cleanup


def refs(chunks) -> set[str]:
    return {c.metadata.get("point_ref") for c in chunks}


@requires_qdrant
class TestCollectionLayout:
    async def test_the_collection_is_created_with_both_vector_kinds(self, store, collection):
        info = await store._client.get_collection(collection)  # noqa: SLF001
        assert "dense" in info.config.params.vectors
        assert "sparse" in (info.config.params.sparse_vectors or {})

    async def test_the_dimension_is_readable_back(self, store, collection):
        assert await store.collection_dimension(collection) == DIM

    async def test_ensure_collection_is_idempotent(self, store, collection):
        # Called on every ingestion. A second call must not recreate anything.
        before = await store.count(collection)
        await store.ensure_collection(collection, DIM)
        await store.ensure_indexes(collection)
        assert await store.count(collection) == before

    async def test_payload_indexes_exist_for_the_scope_fields(self, store, collection):
        info = await store._client.get_collection(collection)  # noqa: SLF001
        schema = info.payload_schema or {}
        for field in ("knowledge_base_id", "document_id", "document_version_id"):
            assert field in schema, field


@requires_qdrant
class TestSparseRetrieval:
    async def test_sparse_search_finds_an_exact_term(self, store, collection):
        """The behaviour the whole Phase 4 change exists for.

        No scrolling, no client-side index: the query is encoded, Qdrant applies
        IDF across the collection and ranks.
        """
        encoded = ENCODER.encode_query("quarterly servicing")
        found = await store.search_sparse(
            collection, SparseVector(encoded.indices, encoded.values), top_k=5
        )
        assert refs(found) == {"p3"}

    async def test_sparse_scores_are_positive_and_ordered(self, store, collection):
        encoded = ENCODER.encode_query("shaft width")
        found = await store.search_sparse(
            collection, SparseVector(encoded.indices, encoded.values), top_k=5
        )
        assert found
        assert all(chunk.score > 0 for chunk in found)
        assert [c.score for c in found] == sorted((c.score for c in found), reverse=True)

    async def test_a_query_with_no_shared_terms_returns_nothing(self, store, collection):
        encoded = ENCODER.encode_query("marine propulsion turbine")
        found = await store.search_sparse(
            collection, SparseVector(encoded.indices, encoded.values), top_k=5
        )
        assert found == []

    async def test_an_empty_sparse_query_returns_nothing(self, store, collection):
        found = await store.search_sparse(collection, SparseVector([], []), top_k=5)
        assert found == []

    async def test_sparse_search_honours_payload_filters(self, store, collection):
        encoded = ENCODER.encode_query("shaft width")
        found = await store.search_sparse(
            collection,
            SparseVector(encoded.indices, encoded.values),
            top_k=5,
            filters={ACTIVE_FIELD: True},
        )
        # p4 is the superseded edition and matches the terms; the filter is the
        # only thing keeping it out of the answer.
        assert "p4" not in refs(found)


@requires_qdrant
class TestDenseRetrieval:
    async def test_dense_search_returns_ranked_results(self, store, collection):
        found = await store.search(collection, fake_vector(PASSAGES[0][4]), top_k=3)
        assert found
        assert [c.score for c in found] == sorted((c.score for c in found), reverse=True)

    async def test_dense_search_honours_payload_filters(self, store, collection):
        found = await store.search(
            collection,
            fake_vector(PASSAGES[0][4]),
            top_k=10,
            filters={"document_id": "doc-2"},
        )
        assert refs(found) == {"p3"}


@requires_qdrant
class TestPayloadOperations:
    async def test_the_active_flag_can_be_flipped_server_side(self, store, collection):
        """One request regardless of how many chunks match.

        This is what makes activating a finished version cheap enough to do as
        a single step, rather than as a second pass over every point.
        """
        await store.set_flag(collection, {"document_version_id": "ver-0"}, ACTIVE_FIELD, True)
        assert await store.count_where(collection, {ACTIVE_FIELD: True}) == 4

        await store.set_flag(collection, {"document_version_id": "ver-0"}, ACTIVE_FIELD, False)
        assert await store.count_where(collection, {ACTIVE_FIELD: True}) == 3

    async def test_deletion_excludes_the_edition_that_just_landed(self, store, collection):
        """The retirement step, against the real must_not filter."""
        removed = await store.delete_where(
            collection,
            {"knowledge_base_id": "kb-test", "document_id": "doc-1"},
            exclude={"document_version_id": "ver-1"},
        )
        assert removed == 1  # only the superseded p4

        remaining = await store.count_where(collection, {"document_id": "doc-1"})
        assert remaining == 2

    async def test_deletion_is_precise_to_one_document(self, store, collection):
        await store.delete_where(collection, {"document_id": "doc-1"})
        assert await store.count_where(collection, {"document_id": "doc-2"}) == 1

    async def test_deleting_twice_removes_nothing_the_second_time(self, store, collection):
        assert await store.delete_where(collection, {"document_id": "doc-2"}) == 1
        assert await store.delete_where(collection, {"document_id": "doc-2"}) == 0

    async def test_deleting_with_an_empty_filter_is_refused(self, store, collection):
        # A filter that came out empty by accident would take out the whole
        # knowledge base.
        with pytest.raises(ValueError):
            await store.delete_where(collection, {})

    async def test_upsert_is_idempotent(self, store, collection):
        before = await store.count(collection)
        encoded = ENCODER.encode(PASSAGES[0][4])
        await store.upsert(
            collection,
            [
                VectorRecord(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, "p1")),
                    vector=fake_vector(PASSAGES[0][4]),
                    text=PASSAGES[0][4],
                    document_id="doc-1",
                    sparse=SparseVector(encoded.indices, encoded.values),
                    metadata={"knowledge_base_id": "kb-test", ACTIVE_FIELD: True},
                )
            ],
        )
        assert await store.count(collection) == before
