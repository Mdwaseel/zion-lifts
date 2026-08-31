from app.retrieval.hybrid_search import reciprocal_rank_fusion
from app.retrieval.keyword_search import BM25Index, tokenize
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


def test_bm25_ranks_the_matching_document_first():
    index = BM25Index.build(
        [
            "qdrant stores dense vectors for similarity search",
            "the weather in paris is mild in spring",
            "postgres is a relational database",
        ]
    )
    scores = index.score(tokenize("qdrant vector search"))
    assert scores[0] == max(scores)
    assert scores[1] == 0.0
