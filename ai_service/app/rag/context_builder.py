"""Assemble retrieved chunks into a numbered, budgeted context block."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.api.schemas.chat import Message
from app.core.constants import MAX_CONTEXT_CHARS
from app.ingestion.processors.cleaner import strip_page_markers
from app.vectorstore.base import ScoredChunk

PASSAGE_TEMPLATE = "[{marker}] {source}\n{text}"


@dataclass(slots=True)
class BuiltContext:
    text: str
    used: list[ScoredChunk] = field(default_factory=list)
    dropped: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.used


def _source_label(chunk: ScoredChunk) -> str:
    meta = chunk.metadata
    title = meta.get("title") or meta.get("source") or chunk.document_id or "unknown source"
    page = meta.get("page")
    return f"{title} (p. {page})" if page else str(title)


class ContextBuilder:
    """Numbers passages so the model can cite them, and enforces a character
    budget so a long retrieval set cannot overflow the model's window."""

    def __init__(self, max_chars: int = MAX_CONTEXT_CHARS, dedupe: bool = True) -> None:
        self._max_chars = max_chars
        self._dedupe = dedupe

    def build(self, chunks: list[ScoredChunk]) -> BuiltContext:
        blocks: list[str] = []
        used: list[ScoredChunk] = []
        seen: set[str] = set()
        budget = self._max_chars
        dropped = 0

        for chunk in chunks:
            body = strip_page_markers(chunk.text).strip()
            if not body:
                continue

            fingerprint = body[:200].lower()
            if self._dedupe and fingerprint in seen:
                dropped += 1
                continue

            block = PASSAGE_TEMPLATE.format(
                marker=len(used) + 1, source=_source_label(chunk), text=body
            )
            if len(block) > budget:
                dropped += 1
                continue

            seen.add(fingerprint)
            blocks.append(block)
            used.append(chunk)
            budget -= len(block) + 2

        return BuiltContext(text="\n\n".join(blocks), used=used, dropped=dropped)

    @staticmethod
    def render_history(history: list[Message], max_turns: int = 6) -> str:
        recent = history[-max_turns:]
        return "\n".join(f"{m.role.value.capitalize()}: {m.content}" for m in recent)
