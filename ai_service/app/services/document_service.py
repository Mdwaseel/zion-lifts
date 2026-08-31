"""Application service backing the document routes."""

from __future__ import annotations

from app.api.schemas.document import (
    DeleteResponse,
    DocumentMetadata,
    DocumentResponse,
    IngestTextRequest,
    IngestUrlRequest,
)
from app.core.constants import MAX_UPLOAD_BYTES, DocumentStatus, SourceType
from app.core.logging import get_logger
from app.ingestion.service import IngestionResult, IngestionService

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md", ".markdown", ".rst", ".csv", ".json")


class UnsupportedFileError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


class DocumentService:
    def __init__(self, ingestion: IngestionService) -> None:
        self._ingestion = ingestion

    @staticmethod
    def _to_response(result: IngestionResult, metadata: DocumentMetadata) -> DocumentResponse:
        enriched = metadata.model_copy(update={"title": metadata.title or result.title})
        return DocumentResponse(
            document_id=result.document_id,
            status=DocumentStatus.INDEXED,
            chunk_count=result.chunk_count,
            collection=result.collection,
            metadata=enriched,
        )

    async def ingest_text(self, request: IngestTextRequest) -> DocumentResponse:
        result = await self._ingestion.ingest_text(
            text=request.text,
            metadata=request.metadata.model_dump(exclude_none=True),
            collection=request.collection,
        )
        return self._to_response(result, request.metadata)

    async def ingest_url(self, request: IngestUrlRequest) -> DocumentResponse:
        metadata = request.metadata.model_copy(update={"source_type": SourceType.WEB})
        result = await self._ingestion.ingest_url(
            url=str(request.url),
            metadata=metadata.model_dump(exclude_none=True),
            collection=request.collection,
        )
        return self._to_response(result, metadata)

    async def ingest_upload(
        self,
        data: bytes,
        filename: str,
        metadata: DocumentMetadata | None = None,
        collection: str | None = None,
    ) -> DocumentResponse:
        if len(data) > MAX_UPLOAD_BYTES:
            raise FileTooLargeError(
                f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
            )
        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            raise UnsupportedFileError(
                f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        source_type = SourceType.PDF if filename.lower().endswith(".pdf") else SourceType.TEXT
        meta = (metadata or DocumentMetadata()).model_copy(
            update={"source_type": source_type, "source": filename}
        )

        result = await self._ingestion.ingest_file(
            data=data,
            filename=filename,
            metadata=meta.model_dump(exclude_none=True),
            collection=collection,
        )
        return self._to_response(result, meta)

    async def delete(self, document_id: str, collection: str | None = None) -> DeleteResponse:
        removed = await self._ingestion.delete_document(document_id, collection)
        return DeleteResponse(document_id=document_id, deleted_chunks=removed)
