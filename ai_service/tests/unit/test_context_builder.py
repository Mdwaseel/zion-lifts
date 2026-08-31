from app.rag.context_builder import ContextBuilder
from app.vectorstore.base import ScoredChunk


def chunk(cid: str, text: str, title: str = "Doc") -> ScoredChunk:
    return ScoredChunk(
        id=cid, text=text, document_id="d1", score=0.5, metadata={"title": title}
    )


def test_passages_are_numbered_from_one():
    built = ContextBuilder().build([chunk("a", "First."), chunk("b", "Second.")])
    assert built.text.startswith("[1] Doc")
    assert "[2] Doc" in built.text
    assert len(built.used) == 2


def test_duplicate_passages_are_dropped():
    built = ContextBuilder().build([chunk("a", "Same text."), chunk("b", "Same text.")])
    assert len(built.used) == 1
    assert built.dropped == 1


def test_budget_stops_oversized_context():
    big = [chunk(str(i), f"passage {i} " + "word " * 500) for i in range(10)]
    built = ContextBuilder(max_chars=3000).build(big)
    assert len(built.text) <= 3000
    assert built.dropped > 0


def test_page_numbers_appear_in_the_source_label():
    passage = ScoredChunk(
        id="a",
        text="Body.",
        document_id="d1",
        score=0.5,
        metadata={"title": "Handbook", "page": 12},
    )
    assert "Handbook (p. 12)" in ContextBuilder().build([passage]).text


def test_empty_retrieval_is_flagged():
    assert ContextBuilder().build([]).is_empty
