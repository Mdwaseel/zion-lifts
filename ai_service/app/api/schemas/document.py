"""Request/response models for the document API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, HttpUrl, field_validator

from app.api.schemas.common import BaseSchema
from app.core.constants import DocumentStatus, JobOperation, SourceType


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


class IngestionRequest(BaseSchema):
    """The contract the Celery worker will receive, once it exists.

    Defined now, ahead of the worker, because it is the interface between two
    services that must not import each other: Django builds this payload from
    its own records, and the shape is the only thing the two sides share. Every
    field is an identifier or a hash — no file bytes and no business data, so
    the broker never carries a document.

    ``file_reference`` is a storage key resolved by the worker, not a path the
    worker is trusted to open blindly; ``content_hash`` is what makes a repeated
    delivery of the same message idempotent rather than duplicative.
    """

    # The correlation id from the HTTP request that caused this ingestion, so
    # one upload can be followed across both services. Optional: a run started
    # by a management command has no originating request, and the worker falls
    # back to the job id.
    request_id: str = Field(default="", max_length=64)
    job_id: str = Field(min_length=1, max_length=64)
    document_id: str = Field(min_length=1, max_length=64)
    document_version_id: str = Field(min_length=1, max_length=64)
    knowledge_base_id: str = Field(min_length=1, max_length=64)
    file_reference: str = Field(default="", max_length=1024)
    content_hash: str = Field(default="", max_length=128)
    embedding_model: str = Field(default="", max_length=200)
    embedding_model_version: str = Field(default="", max_length=40)
    # Which task this message is for. Carried in the body as well as in the task
    # name so a report can name the operation it belongs to without the worker
    # having to infer it from which function it happens to be running in.
    operation: JobOperation = JobOperation.INGEST

    @field_validator("file_reference")
    @classmethod
    def _no_traversal(cls, v: str) -> str:
        """A storage key, never a filesystem path. The worker resolves it
        against configured storage; anything that could escape that root is
        rejected here rather than at the point it is opened."""
        cleaned = v.strip()
        if not cleaned or cleaned.startswith(("/", "\\")) or ".." in cleaned:
            raise ValueError("file_reference must be a relative storage key without '..'")
        return cleaned


class IngestionReport(BaseSchema):
    """One status update from the worker to the backend.

    The same shape carries progress, success and failure — one protocol rather
    than three, so the backend has a single handler and a single set of rules
    about which updates it will accept.

    The three identifiers are all sent, and the backend checks that they
    actually describe each other before it writes anything. A worker that has
    the job id is not thereby trusted about which document that job belongs to.
    """

    job_id: str = Field(min_length=1, max_length=64)
    document_id: str = Field(min_length=1, max_length=64)
    document_version_id: str = Field(min_length=1, max_length=64)

    # The lifecycle stage just entered or completed.
    stage: DocumentStatus
    progress: int = Field(default=0, ge=0, le=100)

    # Measured during this run, never taken from the request. A count the worker
    # was told rather than one it observed would describe the document the
    # backend already thought it had.
    page_count: int | None = None
    chunk_count: int | None = None

    embedding_model: str | None = None
    embedding_model_version: str | None = None
    embedding_dimension: int | None = None
    collection: str | None = None

    error_code: str | None = None
    error_message: str | None = None


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
    """Retrieval without generation. Scoped exactly like ChatRequest, and for
    the same reason — see the note there."""

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    knowledge_base_id: str | None = Field(default=None, max_length=64)
    document_ids: list[str] = Field(default_factory=list, max_length=50)

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
