"""Build the per-chunk payload that ends up in the vector store."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.ingestion.processors.chunker import Chunk
from app.ingestion.processors.cleaner import page_of

_WORD = re.compile(r"\w+", re.UNICODE)


def new_document_id() -> str:
    return uuid.uuid4().hex


def chunk_id(document_id: str, index: int) -> str:
    """Deterministic UUID so re-ingesting a document overwrites its own chunks."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}/{index}"))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def derive_title(text: str, fallback: str | None = None) -> str | None:
    for line in text.splitlines():
        candidate = line.strip()
        if 3 <= len(candidate) <= 120:
            return candidate
    return fallback


def build_payload(
    chunk: Chunk,
    document_id: str,
    base: dict[str, Any],
    total_chunks: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "document_id": document_id,
        "chunk_index": chunk.index,
        "total_chunks": total_chunks,
        "char_count": chunk.char_count,
        "word_count": len(_WORD.findall(chunk.text)),
        "content_hash": content_hash(chunk.text),
        "indexed_at": datetime.now(UTC).isoformat(),
    }
    page = page_of(chunk.text)
    if page is not None:
        payload["page"] = page

    for key, value in {**base, **chunk.metadata}.items():
        if value is not None and key not in payload:
            payload[key] = value
    return payload
