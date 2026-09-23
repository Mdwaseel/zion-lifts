"""Chat and search endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.api.schemas.common import ErrorResponse
from app.api.schemas.document import SearchRequest, SearchResponse
from app.core.logging import get_logger
from app.core.security import require_api_key
from app.llm.fallback import AllProvidersFailedError
from app.services.chat_service import ChatService, ScopeError

logger = get_logger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_api_key)],
    responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)


async def _sse(service: ChatService, request: ChatRequest) -> AsyncIterator[str]:
    async for chunk in service.stream(request):
        yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("", response_model=ChatResponse, summary="Ask a grounded question")
async def ask(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        return await service.ask(request)
    except ScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except AllProvidersFailedError as exc:
        logger.error("all llm providers failed", extra={"errors": exc.errors})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No language model provider is currently available.",
        ) from exc


@router.post("/stream", summary="Ask a question, streamed as SSE")
async def ask_stream(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    return StreamingResponse(
        _sse(service, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/search", response_model=SearchResponse, summary="Retrieval without generation")
async def search(
    request: SearchRequest,
    service: ChatService = Depends(get_chat_service),
) -> SearchResponse:
    """Returns the ranked passages only. Useful for debugging retrieval quality."""
    try:
        return await service.search(request)
    except ScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
