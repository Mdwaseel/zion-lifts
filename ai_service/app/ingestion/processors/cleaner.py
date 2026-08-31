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
