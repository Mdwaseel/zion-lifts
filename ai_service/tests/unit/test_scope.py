"""Retrieval scope and collection naming — the read boundary.

These two together decide what a request can see. The tests below are mostly
about what a scope *refuses* to do, because the failure they guard against is
not a wrong answer but a request reading a corpus it was never granted.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.retrieval.scope import RetrievalScope
from app.vectorstore.collections import CollectionNameBuilder

MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class TestCollectionNaming:
    def test_the_name_carries_the_corpus_and_the_embedding(self):
        name = CollectionNameBuilder.build("kb-7", MODEL, "v1")
        assert name == "kb_kb_7__sentence_transformers_all_minilm_l6_v2_v1"

    def test_the_organisation_is_part_of_the_model_segment(self):
        # `org-a/embed` and `org-b/embed` are different models producing
        # incomparable vectors. Keeping only the segment after the slash would
        # have put them in one collection.
        assert CollectionNameBuilder.build(
            "kb-7", "org-a/embed", "v1"
        ) != CollectionNameBuilder.build("kb-7", "org-b/embed", "v1")

    def test_long_model_names_stay_unique_after_truncation(self):
        prefix = "a-very-long-organisation-name-indeed/embedding-model"
        assert CollectionNameBuilder.build(
            "kb-7", f"{prefix}-alpha", "v1"
        ) != CollectionNameBuilder.build("kb-7", f"{prefix}-beta", "v1")

    def test_the_dimension_is_part_of_the_name_when_known(self):
        assert CollectionNameBuilder.build("kb-7", MODEL, "v1", 384).endswith("_d384")
        assert not CollectionNameBuilder.build("kb-7", MODEL, "v1").endswith("_d384")

    def test_two_widths_never_share_a_collection(self):
        assert CollectionNameBuilder.build("kb-7", MODEL, "v1", 384) != CollectionNameBuilder.build(
            "kb-7", MODEL, "v1", 768
        )

    def test_two_embedding_versions_never_share_a_collection(self):
        # The whole point: 384-dimensional vectors cannot be written into a
        # collection built for 768, and cannot be compared with them either.
        first = CollectionNameBuilder.build("kb-7", MODEL, "v1")
        second = CollectionNameBuilder.build("kb-7", MODEL, "v2")
        assert first != second

    def test_two_models_never_share_a_collection(self):
        assert CollectionNameBuilder.build("kb-7", MODEL, "v1") != CollectionNameBuilder.build(
            "kb-7", "BAAI/bge-base-en-v1.5", "v1"
        )

    def test_two_knowledge_bases_never_share_a_collection(self):
        assert CollectionNameBuilder.build("kb-7", MODEL, "v1") != CollectionNameBuilder.build(
            "kb-8", MODEL, "v1"
        )

    def test_naming_is_deterministic(self):
        assert CollectionNameBuilder.build("kb-7", MODEL, "v1") == CollectionNameBuilder.build(
            "kb-7", MODEL, "v1"
        )

    def test_a_uuid_knowledge_base_id_is_usable(self):
        name = CollectionNameBuilder.build("3f2a9c1e-1111-2222-3333-444455556666", MODEL, "v1")
        assert name.startswith("kb_3f2a9c1e")
        assert all(c.isalnum() or c == "_" for c in name)

    def test_unsafe_characters_never_reach_the_name(self):
        name = CollectionNameBuilder.build("../../etc; drop", MODEL, "v1")
        for char in "./;\\ ":
            assert char not in name

    def test_an_empty_knowledge_base_id_is_refused(self):
        with pytest.raises(ValueError):
            CollectionNameBuilder.build("", MODEL, "v1")

    def test_a_generated_name_is_recognisable(self):
        assert CollectionNameBuilder.is_generated(CollectionNameBuilder.build("k", MODEL, "v1"))
        assert not CollectionNameBuilder.is_generated("zion_lift_documents")


class TestRetrievalScope:
    def test_a_knowledge_base_scope_filters_by_knowledge_base(self):
        scope = RetrievalScope.for_knowledge_base("kb-7")
        # `active` joins it from Phase 3: a knowledge base's collection holds
        # every version of every document, including ones still being written.
        assert scope.to_filters() == {"knowledge_base_id": "kb-7", "active": True}

    def test_a_scope_never_sees_an_inactive_version(self):
        # The filter that keeps a half-written edition out of an answer, and
        # keeps the previous edition answering until its replacement is whole.
        assert RetrievalScope.for_knowledge_base("kb-7").to_filters()["active"] is True

    def test_document_ids_narrow_the_scope_further(self):
        scope = RetrievalScope.for_knowledge_base("kb-7", document_ids=["d1", "d2"])
        filters = scope.to_filters()
        assert filters["knowledge_base_id"] == "kb-7"
        assert filters["document_id"] == ["d1", "d2"]

    def test_one_document_stays_an_equality_match(self):
        # So it uses the payload index directly rather than a set membership.
        scope = RetrievalScope.for_knowledge_base("kb-7", document_ids=["d1"])
        assert scope.to_filters()["document_id"] == "d1"

    def test_a_scope_cannot_be_built_without_a_knowledge_base(self):
        with pytest.raises(ValueError):
            RetrievalScope.for_knowledge_base("")

    def test_the_filter_always_contains_the_knowledge_base(self):
        # The property that matters: there is no way to construct a
        # knowledge-base scope whose filter would match another corpus.
        scope = RetrievalScope.for_knowledge_base("kb-7", document_ids=[])
        assert "knowledge_base_id" in scope.to_filters()

    def test_the_collection_follows_the_embedding(self):
        scope = RetrievalScope.for_knowledge_base("kb-7")
        assert scope.collection_for(MODEL, "v1") != scope.collection_for(MODEL, "v2")

    def test_a_scope_is_immutable(self):
        # It is an authorisation decision; nothing downstream may widen it.
        scope = RetrievalScope.for_knowledge_base("kb-7")
        with pytest.raises(dataclasses.FrozenInstanceError):
            scope.knowledge_base_id = "kb-8"  # type: ignore[misc]

    def test_permissions_are_carried_but_never_logged(self):
        scope = RetrievalScope.for_knowledge_base("kb-7", permissions={"read:all"})
        assert "read:all" in scope.permissions
        assert "read:all" not in str(scope.describe())


class TestLegacyScope:
    def test_the_legacy_scope_reads_its_configured_collection(self):
        scope = RetrievalScope.legacy("zion_lift_documents")
        assert scope.collection_for(MODEL, "v1") == "zion_lift_documents"

    def test_the_legacy_scope_needs_no_filter(self):
        # That collection holds exactly one corpus, so its name is already the
        # whole boundary.
        assert RetrievalScope.legacy("zion_lift_documents").to_filters() == {}

    def test_the_legacy_scope_is_flagged(self):
        assert RetrievalScope.legacy("c").is_legacy
        assert not RetrievalScope.for_knowledge_base("kb-7").is_legacy

    def test_a_legacy_scope_needs_a_collection_name(self):
        with pytest.raises(ValueError):
            RetrievalScope.legacy("")
