"""Document ingestion and management endpoints."""

from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.api.deps import get_document_service
from app.api.schemas.common import ErrorResponse
from app.api.schemas.document import (
    DeleteResponse,
    DocumentMetadata,
    DocumentResponse,
    IngestTextRequest,
    IngestUrlRequest,
)
from app.core.logging import get_logger
from app.core.security import require_api_key
from app.services.document_service import (
    DocumentService,
    FileTooLargeError,
    UnsupportedFileError,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_api_key)],
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)


def _parse_metadata(raw: str | None) -> DocumentMetadata:
    if not raw:
        return DocumentMetadata()
    try:
        return DocumentMetadata.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"metadata must be a valid DocumentMetadata JSON object: {exc}",
        ) from exc


@router.post(
    "/text",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest raw text",
)
async def ingest_text(
    request: IngestTextRequest,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        return await service.ingest_text(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post(
    "/url",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fetch and ingest a web page",
)
async def ingest_url(
    request: IngestUrlRequest,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        return await service.ingest_url(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("url ingestion failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch the URL: {exc}",
        ) from exc


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or text file",
)
async def upload(
    file: UploadFile = File(..., description="PDF, TXT, MD, RST, CSV or JSON."),
    metadata: str | None = Form(None, description="Optional DocumentMetadata as JSON."),
    collection: str | None = Form(None),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    data = await file.read()
    try:
        return await service.ingest_upload(
            data=data,
            filename=file.filename or "upload",
            metadata=_parse_metadata(metadata),
            collection=collection,
        )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except UnsupportedFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    finally:
        await file.close()


@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
    summary="Delete a document and all of its chunks",
)
async def delete_document(
    document_id: str,
    collection: str | None = Query(None),
    service: DocumentService = Depends(get_document_service),
) -> DeleteResponse:
    result = await service.delete(document_id, collection)
    if result.deleted_chunks == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No document found with id {document_id}.",
        )
    return result
