"""Collection naming and payload-index definitions."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import DEFAULT_COLLECTION

# Payload fields that must be indexed for fast filtering in Qdrant.
KEYWORD_INDEXES: tuple[str, ...] = ("document_id", "source_type", "tags", "language")

TEXT_FIELD = "text"
DOCUMENT_ID_FIELD = "document_id"


@dataclass(frozen=True, slots=True)
class CollectionSpec:
    name: str
    vector_size: int
    distance: str = "Cosine"


def resolve(name: str | None, default: str = DEFAULT_COLLECTION) -> str:
    """Pick the caller's collection, falling back to the configured default."""
    return (name or default).strip() or default


def spec_for(name: str, vector_size: int) -> CollectionSpec:
    return CollectionSpec(name=name, vector_size=vector_size)
