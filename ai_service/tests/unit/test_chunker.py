from app.ingestion.processors.chunker import RecursiveChunker


def test_short_text_is_one_chunk():
    chunks = RecursiveChunker(chunk_size=500, chunk_overlap=0).split("A short paragraph.")
    assert len(chunks) == 1
    assert chunks[0].index == 0


def test_long_text_splits_on_paragraph_boundaries():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(6))
    chunks = RecursiveChunker(chunk_size=400, chunk_overlap=0).split(text)
    assert len(chunks) > 1
    assert all(c.char_count <= 400 for c in chunks)


def test_overlap_carries_context_forward():
    text = "\n\n".join("sentence " * 40 for _ in range(4))
    chunks = RecursiveChunker(chunk_size=300, chunk_overlap=50).split(text)
    assert len(chunks) >= 2
    tail = chunks[0].text[-50:].lstrip()
    assert chunks[1].text.startswith(tail[:20])


def test_empty_input_yields_nothing():
    assert RecursiveChunker().split("   ") == []


def test_overlap_must_be_smaller_than_size():
    import pytest

    with pytest.raises(ValueError):
        RecursiveChunker(chunk_size=100, chunk_overlap=100)


def test_metadata_is_copied_per_chunk():
    chunks = RecursiveChunker(chunk_size=100, chunk_overlap=0).split(
        "word " * 200, {"title": "Doc"}
    )
    assert all(c.metadata["title"] == "Doc" for c in chunks)
    chunks[0].metadata["title"] = "Changed"
    assert chunks[1].metadata["title"] == "Doc"
