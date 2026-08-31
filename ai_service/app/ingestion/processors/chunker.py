"""Recursive character chunking with overlap.

Splits on the largest natural boundary that fits (paragraph, then line, then
sentence, then word) so chunks stay semantically coherent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    MIN_CHUNK_CHARS,
)

SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", "")


@dataclass(slots=True)
class Chunk:
    text: str
    index: int
    start: int
    end: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)


class RecursiveChunker:
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        min_chunk_chars: int = MIN_CHUNK_CHARS,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_chars = min_chunk_chars

    def _split(self, text: str, separators: tuple[str, ...]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        if not separators:
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        separator, rest = separators[0], separators[1:]
        if separator == "":
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        pieces = text.split(separator)
        merged: list[str] = []
        buffer = ""
        for piece in pieces:
            candidate = f"{buffer}{separator}{piece}" if buffer else piece
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue
            if buffer:
                merged.append(buffer)
            buffer = piece if len(piece) <= self.chunk_size else ""
            if not buffer:
                merged.extend(self._split(piece, rest))
        if buffer:
            merged.append(buffer)
        return merged

    def split(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        text = (text or "").strip()
        if not text:
            return []

        base = metadata or {}
        pieces = [p.strip() for p in self._split(text, SEPARATORS) if p.strip()]

        chunks: list[Chunk] = []
        cursor = 0
        for piece in pieces:
            if len(piece) < self.min_chunk_chars and chunks:
                # Fold a runt into its predecessor rather than indexing noise.
                previous = chunks[-1]
                previous.text = f"{previous.text}\n{piece}"
                previous.end += len(piece)
                continue

            start = text.find(piece, cursor)
            start = cursor if start == -1 else start
            end = start + len(piece)
            cursor = max(end - self.chunk_overlap, start + 1)

            chunks.append(
                Chunk(text=piece, index=len(chunks), start=start, end=end, metadata=dict(base))
            )

        return self._apply_overlap(chunks, text)

    def _apply_overlap(self, chunks: list[Chunk], source: str) -> list[Chunk]:
        """Prefix each chunk with the tail of the previous one so a fact split
        across a boundary is still retrievable from either side."""
        if self.chunk_overlap <= 0 or len(chunks) < 2:
            return chunks
        for i in range(1, len(chunks)):
            tail = chunks[i - 1].text[-self.chunk_overlap :].lstrip()
            if tail:
                chunks[i].text = f"{tail} {chunks[i].text}"
        return chunks
