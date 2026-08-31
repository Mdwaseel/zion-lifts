"""Application service backing the chat routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.api.schemas.chat import ChatRequest, ChatResponse, StreamChunk, Usage
from app.api.schemas.document import SearchHit, SearchRequest, SearchResponse
from app.core.constants import ConfidenceLevel
from app.core.logging import get_logger
from app.rag.pipeline import RagPipeline

logger = get_logger(__name__)


class ChatService:
    """Translates between API schemas and the RAG pipeline. Route handlers stay
    thin; nothing here knows about FastAPI."""

    def __init__(self, pipeline: RagPipeline) -> None:
        self._pipeline = pipeline

    async def ask(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or uuid.uuid4().hex

        result = await self._pipeline.ask(
            question=request.question,
            history=request.history,
            collection=request.collection,
            top_k=request.top_k,
            filters=request.filters,
        )

        confidence = result.confidence
        usage = result.usage
        logger.info(
            "chat answered",
            extra={
                "session_id": session_id,
                "provider": result.provider,
                "confidence": confidence.score if confidence else 0.0,
                "citations": len(result.citations),
                "took_ms": round(result.took_ms, 1),
            },
        )

        return ChatResponse(
            answer=result.answer,
            citations=result.citations,
            confidence=confidence.score if confidence else 0.0,
            confidence_level=confidence.level if confidence else ConfidenceLevel.LOW,
            session_id=session_id,
            provider=result.provider,
            model=result.model,
            rewritten_query=result.rewritten_query,
            usage=Usage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            ),
            took_ms=round(result.took_ms, 2),
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        try:
            async for event, payload in self._pipeline.ask_stream(
                question=request.question,
                history=request.history,
                collection=request.collection,
                top_k=request.top_k,
                filters=request.filters,
            ):
                if event == "delta":
                    yield StreamChunk(type="delta", content=str(payload))
                elif event == "citations":
                    yield StreamChunk(type="citations", citations=payload)  # type: ignore[arg-type]
                elif event == "done":
                    yield StreamChunk(type="done")
        except Exception as exc:
            logger.exception("stream failed")
            yield StreamChunk(type="error", error=str(exc))

    async def search(self, request: SearchRequest) -> SearchResponse:
        import time

        started = time.perf_counter()
        chunks, _ = await self._pipeline.retrieve(
            question=request.query,
            collection=request.collection,
            top_k=request.top_k,
            filters=request.filters,
        )
        return SearchResponse(
            query=request.query,
            hits=[
                SearchHit(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    text=chunk.text,
                    score=round(float(chunk.score), 4),
                    metadata=chunk.metadata,
                )
                for chunk in chunks
            ],
            took_ms=round((time.perf_counter() - started) * 1000, 2),
        )
