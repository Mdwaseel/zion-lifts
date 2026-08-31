"""Request/response models for the document API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, HttpUrl, field_validator

from app.api.schemas.common import BaseSchema
from app.core.constants import DocumentStatus, SourceType


class DocumentMetadata(BaseSchema):
    title: str | None = None
    source: str | None = None
    source_type: SourceType = SourceType.TEXT
    author: str | None = None
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class IngestTextRequest(BaseSchema):
    text: str = Field(min_length=1, max_length=2_000_000)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    collection: str | None = None


class IngestUrlRequest(BaseSchema):
    url: HttpUrl
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    collection: str | None = None


class ChunkPreview(BaseSchema):
    chunk_id: str
    index: int
    text: str
    char_count: int


class DocumentResponse(BaseSchema):
    document_id: str
    status: DocumentStatus
    chunk_count: int
    collection: str
    metadata: DocumentMetadata
    created_at: datetime | None = None
    error: str | None = None


class DocumentListItem(BaseSchema):
    document_id: str
    title: str | None
    source_type: SourceType
    chunk_count: int
    created_at: datetime | None = None


class DeleteResponse(BaseSchema):
    document_id: str
    deleted_chunks: int


class SearchRequest(BaseSchema):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    collection: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class SearchHit(BaseSchema):
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseSchema):
    query: str
    hits: list[SearchHit]
    took_ms: float
