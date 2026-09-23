"""Application service backing the chat routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.api.schemas.chat import ChatRequest, ChatResponse, StreamChunk, Usage
from app.api.schemas.document import SearchHit, SearchRequest, SearchResponse
from app.core.constants import ConfidenceLevel
from app.core.logging import get_logger
from app.orchestration.assistant import AssistantPipeline
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

    def __init__(
        self,
        pipeline: RagPipeline,
        default_scope: RetrievalScope,
        assistant: AssistantPipeline | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._default_scope = default_scope
        # The routed pipeline answers chat; the RAG pipeline still backs
        # `/chat/search`, which is retrieval without generation and has no
        # intent to route. Optional so a caller that only wants retrieval — the
        # evaluation harness, a retrieval-only test — can build this without
        # standing up a router and a website index.
        self._assistant = assistant

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

        if self._assistant is None:
            return await self._ask_unrouted(request, scope, session_id)

        result = await self._assistant.ask(
            question=request.question,
            scope=scope,
            history=request.history,
            top_k=request.top_k,
        )

        usage = result.usage
        logger.info(
            "chat answered",
            extra={
                "session_id": session_id,
                "intent": result.intent,
                "behaviour": result.behaviour,
                "provider": result.provider,
                "confidence": result.confidence.score,
                "citations": len(result.citations),
                "related_pages": len(result.related_pages),
                "took_ms": round(result.took_ms, 1),
                **scope.describe(),
            },
        )

        return ChatResponse(
            answer=result.answer,
            citations=result.citations,
            confidence=result.confidence.score,
            confidence_level=result.confidence.level,
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
            intent=result.intent,
            related_pages=result.related_pages,
            suggested_questions=result.suggested_questions,
        )

    async def _ask_unrouted(
        self, request: ChatRequest, scope: RetrievalScope, session_id: str
    ) -> ChatResponse:
        """The pre-routing behaviour, kept for callers built without a router.

        Retrieve, ground, answer or refuse. It is the path the evaluation
        harness uses to measure retrieval in isolation, and the reason the
        routed pipeline could be added without rewriting what it replaced.
        """
        result = await self._pipeline.ask(
            question=request.question,
            scope=scope,
            history=request.history,
            top_k=request.top_k,
        )
        confidence = result.confidence
        usage = result.usage
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
        """Server-sent events, in the order the front end reads them.

        ``metadata`` first (when routing is in play), then ``delta`` until the
        answer is complete, then ``citations``, then any attachments, then
        ``done``. A client that predates the new event types ignores the ones it
        does not recognise, which is why they were added as new ``type`` values
        rather than as new fields on ``delta``.
        """
        try:
            scope = self._scope_for(request.knowledge_base_id, request.document_ids)
            source = self._assistant or self._pipeline
            async for event, payload in source.ask_stream(
                question=request.question,
                scope=scope,
                history=request.history,
                top_k=request.top_k,
            ):
                chunk = self._as_chunk(event, payload)
                if chunk is not None:
                    yield chunk
        except Exception as exc:
            logger.exception("stream failed")
            yield StreamChunk(type="error", error=str(exc))

    @staticmethod
    def _as_chunk(event: str, payload: object) -> StreamChunk | None:
        """One pipeline event as one SSE payload. Unknown events are dropped."""
        if event == "delta":
            return StreamChunk(type="delta", content=str(payload))
        if event == "citations":
            return StreamChunk(type="citations", citations=payload)  # type: ignore[arg-type]
        if event == "related_pages":
            return StreamChunk(type="related_pages", related_pages=payload)  # type: ignore[arg-type]
        if event == "suggestions":
            return StreamChunk(type="suggestions", suggested_questions=payload)  # type: ignore[arg-type]
        if event == "metadata" and isinstance(payload, dict):
            return StreamChunk(
                type="metadata",
                intent=payload.get("intent"),
                confidence=payload.get("confidence"),
                confidence_level=payload.get("level"),
            )
        if event == "done":
            return StreamChunk(type="done")
        return None

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
