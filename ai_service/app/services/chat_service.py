"""Application service backing the chat routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.api.schemas.chat import ChatRequest, ChatResponse, StreamChunk, Usage
from app.api.schemas.document import SearchHit, SearchRequest, SearchResponse
from app.core.constants import ConfidenceLevel
from app.core.logging import get_logger
from app.rag.pipeline import RagPipeline
from app.retrieval.scope import RetrievalScope

logger = get_logger(__name__)


class ScopeError(ValueError):
    """The caller asked for a corpus it cannot have, or described one that
    makes no sense. Surfaced as a 422, never as an empty result — silently
    searching something other than what was asked for is worse than refusing."""


class ChatService:
    """Translates between API schemas and the RAG pipeline. Route handlers stay
    thin; nothing here knows about FastAPI.

    It is also where a request stops being able to choose its own corpus: the
    caller may name a knowledge base, and this class turns that into a
    :class:`RetrievalScope`. Once permissions exist the check goes in
    ``_scope_for`` and every caller inherits it, because it is the only route
    from a request to a search.
    """

    def __init__(self, pipeline: RagPipeline, default_scope: RetrievalScope) -> None:
        self._pipeline = pipeline
        self._default_scope = default_scope

    def _scope_for(self, knowledge_base_id: str | None, document_ids: list[str]) -> RetrievalScope:
        if not knowledge_base_id:
            # The service default, which for a single-corpus deployment is the
            # legacy collection named in configuration.
            if not document_ids:
                return self._default_scope
            raise ScopeError("document_ids requires a knowledge_base_id")

        return RetrievalScope.for_knowledge_base(
            knowledge_base_id=knowledge_base_id,
            document_ids=document_ids,
        )

    async def ask(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or uuid.uuid4().hex
        scope = self._scope_for(request.knowledge_base_id, request.document_ids)

        result = await self._pipeline.ask(
            question=request.question,
            scope=scope,
            history=request.history,
            top_k=request.top_k,
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
                **scope.describe(),
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
            scope = self._scope_for(request.knowledge_base_id, request.document_ids)
            async for event, payload in self._pipeline.ask_stream(
                question=request.question,
                scope=scope,
                history=request.history,
                top_k=request.top_k,
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
            scope=self._scope_for(request.knowledge_base_id, request.document_ids),
            top_k=request.top_k,
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
