from app.rag.citation_handler import (
    build_citations,
    extract_markers,
    strip_invalid_markers,
)
from app.vectorstore.base import ScoredChunk


def chunks(n: int) -> list[ScoredChunk]:
    return [
        ScoredChunk(
            id=f"c{i}",
            text=f"Passage number {i} with supporting detail.",
            document_id=f"d{i}",
            score=0.9 - i * 0.1,
            metadata={"title": f"Doc {i}", "source": f"file{i}.pdf"},
        )
        for i in range(1, n + 1)
    ]


def test_markers_are_extracted_in_order_without_duplicates():
    assert extract_markers("A [2] then [1] then [2] again.") == [2, 1]


def test_hallucinated_markers_are_removed():
    assert strip_invalid_markers("Fact [1] and claim [9].", 2) == "Fact [1] and claim."


def test_valid_markers_survive():
    assert strip_invalid_markers("Fact [1] and [2].", 2) == "Fact [1] and [2]."


def test_citations_resolve_to_the_right_chunks():
    citations = build_citations("Claim [2] and claim [1].", chunks(3))
    assert [c.marker for c in citations] == ["[2]", "[1]"]
    assert citations[0].document_id == "d2"
    assert citations[0].title == "Doc 2"


def test_uncited_answer_produces_no_citations():
    assert build_citations("No markers here.", chunks(3)) == []


def test_out_of_range_marker_is_ignored():
    assert build_citations("Claim [5].", chunks(2)) == []
