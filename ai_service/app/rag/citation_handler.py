"""Map inline [n] markers in a generated answer back to source chunks."""

from __future__ import annotations

import re

from app.api.schemas.chat import Citation
from app.vectorstore.base import ScoredChunk

MARKER_RE = re.compile(r"\[(\d{1,2})\]")
SNIPPET_CHARS = 280


def _snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit]
    return cut[: cut.rfind(" ")].rstrip(",;:") + "\u2026"


def extract_markers(answer: str) -> list[int]:
    """Markers in order of first appearance."""
    seen: list[int] = []
    for match in MARKER_RE.finditer(answer):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return seen


def strip_invalid_markers(answer: str, valid_count: int) -> str:
    """Drop citations pointing past the end of the context.

    A model that hallucinates [7] against four passages would otherwise ship a
    citation that resolves to nothing.
    """

    def replace(match: re.Match[str]) -> str:
        number = int(match.group("n"))
        return match.group(0) if 1 <= number <= valid_count else ""

    cleaned = re.sub(r"\[(?P<n>\d{1,2})\]", replace, answer)
    cleaned = re.sub(r" +([.,;:])", lambda m: m.group(1), cleaned)  # tidy space before punctuation
    return re.sub(r"[ ]{2,}", " ", cleaned).strip()


def build_citations(answer: str, chunks: list[ScoredChunk]) -> list[Citation]:
    """Return only the passages the answer actually cited, in citation order."""
    citations: list[Citation] = []
    for number in extract_markers(answer):
        if not 1 <= number <= len(chunks):
            continue
        chunk = chunks[number - 1]
        meta = chunk.metadata
        citations.append(
            Citation(
                marker=f"[{number}]",
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                title=meta.get("title"),
                source=meta.get("source"),
                snippet=_snippet(chunk.text),
                score=round(float(chunk.score), 4),
            )
        )
    return citations


def fallback_citations(chunks: list[ScoredChunk], limit: int = 3) -> list[Citation]:
    """Used when the model answered without citing anything."""
    return [
        Citation(
            marker=f"[{i}]",
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            title=chunk.metadata.get("title"),
            source=chunk.metadata.get("source"),
            snippet=_snippet(chunk.text),
            score=round(float(chunk.score), 4),
        )
        for i, chunk in enumerate(chunks[:limit], start=1)
    ]
