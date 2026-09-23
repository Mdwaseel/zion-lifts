"""Normalise raw extracted text before chunking."""

from __future__ import annotations

import re
import unicodedata

_PAGE_MARKER = re.compile(r"\[\[page:(\d+)\]\]")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t\u00a0]{2,}")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BULLETS = re.compile(r"^[\u2022\u25cf\u25aa\u00b7\-\*]\s+", re.MULTILINE)


def clean_text(text: str, keep_page_markers: bool = True) -> str:
    """Fix the artefacts that PDF and HTML extraction reliably introduce."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)  # rejoin words split across lines
    text = _BULLETS.sub("- ", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_NEWLINE.sub("\n\n", text)

    if not keep_page_markers:
        text = _PAGE_MARKER.sub("", text)

    return text.strip()


def strip_page_markers(text: str) -> str:
    return _MULTI_SPACE.sub(" ", _PAGE_MARKER.sub("", text)).strip()


def page_of(text: str, default: int | None = None) -> int | None:
    """Read the page number a chunk starts on, if a marker survived."""
    match = _PAGE_MARKER.search(text)
    return int(match.group(1)) if match else default


def last_page_in(text: str, default: int | None = None) -> int | None:
    """The last page a chunk touches, if any marker survived in it."""
    matches = _PAGE_MARKER.findall(text)
    return int(matches[-1]) if matches else default


def assign_pages(texts: list[str], first_page: int = 1) -> list[int | None]:
    """Page number for each chunk in order, carrying the last one forward.

    A marker only appears where a page *starts*, so most chunks contain none —
    a chunk from the middle of page twelve has nothing in it that says twelve.
    Reading each chunk in isolation therefore leaves the majority of a document
    with no page at all, and a citation without a page cannot be followed back
    to the source, which is most of what a citation is for.

    Walking the chunks in order and carrying the last marker forward fixes that:
    a chunk with no marker belongs to whichever page was open when it started.
    """
    pages: list[int | None] = []
    current: int | None = first_page
    for text in texts:
        # The page a chunk *starts* on is what it should be cited as, even when
        # it runs over onto the next one.
        start = page_of(text)
        if start is not None:
            current = start
        pages.append(current)
        # A chunk spanning a boundary leaves the following chunks on the later
        # page, so the carried value is the last marker seen, not the first.
        current = last_page_in(text, current)
    return pages
