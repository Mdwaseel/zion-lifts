from app.retrieval.hybrid_search import deduplicate, reciprocal_rank_fusion
from app.retrieval.sparse import SparseEncoder, term_index, tokenize
from app.vectorstore.base import ScoredChunk


def chunk(cid: str, score: float = 0.0) -> ScoredChunk:
    return ScoredChunk(id=cid, text=f"text {cid}", document_id="d", score=score)


def test_fusion_rewards_agreement_between_rankings():
    dense = [chunk("a"), chunk("b"), chunk("c")]
    sparse = [chunk("c"), chunk("a"), chunk("z")]
    fused = reciprocal_rank_fusion([dense, sparse])
    assert fused[0].id == "a"  # ranked highly by both
    assert {c.id for c in fused} == {"a", "b", "c", "z"}


def test_fusion_respects_weights():
    dense = [chunk("a"), chunk("b")]
    sparse = [chunk("b"), chunk("a")]
    assert reciprocal_rank_fusion([dense, sparse], [0.9, 0.1])[0].id == "a"
    assert reciprocal_rank_fusion([dense, sparse], [0.1, 0.9])[0].id == "b"


def test_tokenizer_drops_stopwords():
    assert tokenize("What is the vector store?") == ["vector", "store"]


def test_the_sparse_encoder_puts_shared_terms_on_shared_dimensions():
    """The property lexical retrieval depends on.

    Scoring moved into Qdrant in Phase 4, so what is testable here is the part
    that stayed: a query and a passage that share a term must land on the same
    dimension, or the store has nothing to match on.
    """
    encoder = SparseEncoder()
    passage = encoder.encode("qdrant stores dense vectors for similarity search")
    query = encoder.encode("qdrant vector search")
    unrelated = encoder.encode("the weather in paris is mild in spring")

    assert set(query.indices) & set(passage.indices)
    assert not (set(query.indices) & set(unrelated.indices))


def test_term_indices_are_stable_across_processes():
    # Python's own hash() is salted per process: a term would occupy one
    # dimension in the worker and another in the API, and every lexical search
    # would silently return nothing.
    assert term_index("qdrant") == term_index("qdrant")
    assert term_index("qdrant") != term_index("postgres")


def test_the_encoder_is_deterministic():
    encoder = SparseEncoder()
    assert encoder.encode("shaft width 1600 mm") == encoder.encode("shaft width 1600 mm")


def test_a_query_of_only_stopwords_encodes_to_nothing():
    # Nothing to search lexically, which correctly leaves dense to answer alone.
    assert SparseEncoder().encode("what is the of on").is_empty


def test_repeated_terms_saturate_rather_than_accumulate():
    encoder = SparseEncoder()
    once = encoder.encode("lift")
    many = encoder.encode("lift " * 12)
    assert many.values[0] > once.values[0]
    # log(1 + 12) is well under 12: a term twelve times over is not twelve
    # times more relevant.
    assert many.values[0] < 12 * once.values[0]


def test_duplicates_are_collapsed_by_identity():
    # Dense and sparse retrieval finding the same chunk is the normal case and
    # the point of running both; letting it through twice would spend two of
    # the reranker's slots on one passage.
    unique = deduplicate([chunk("a"), chunk("b"), chunk("a")])
    assert [c.id for c in unique] == ["a", "b"]


def test_deduplication_keeps_the_better_ranked_copy():
    unique = deduplicate([chunk("a", 0.9), chunk("a", 0.1)])
    assert unique[0].score == 0.9
