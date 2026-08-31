from app.ingestion.processors.cleaner import clean_text, page_of, strip_page_markers


def test_collapses_whitespace_and_newlines():
    assert clean_text("a  b\n\n\n\nc") == "a b\n\nc"


def test_rejoins_hyphenated_line_breaks():
    assert "retrieval" in clean_text("retrie-\nval augmented")


def test_strips_control_characters():
    assert clean_text("clean\x00text") == "cleantext"


def test_normalises_bullets():
    assert clean_text("\u2022 first\n\u2022 second").startswith("- first")


def test_page_markers_survive_cleaning_and_are_readable():
    cleaned = clean_text("[[page:7]]\n\nSome body text.")
    assert page_of(cleaned) == 7
    assert "[[page:" not in strip_page_markers(cleaned)


def test_empty_input():
    assert clean_text("") == ""
