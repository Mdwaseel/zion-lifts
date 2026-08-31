"""Generate a grounded answer from assembled context."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.api.schemas.chat import Citation, Message
from app.core.logging import get_logger
from app.llm.base import LLMClient, LLMMessage, LLMUsage
from app.prompts.rag import RAG_SYSTEM, build_rag_prompt
from app.prompts.system import REFUSAL_TEXT
from app.rag.citation_handler import (
    build_citations,
    fallback_citations,
    strip_invalid_markers,
)
from app.rag.context_builder import BuiltContext, ContextBuilder
from app.vectorstore.base import ScoredChunk

logger = get_logger(__name__)

INSUFFICIENT_MARKER = "INSUFFICIENT_CONTEXT"


@dataclass(slots=True)
class GeneratedAnswer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    grounded: bool = True


class AnswerGenerator:
    def __init__(
        self,
        llm: LLMClient,
        context_builder: ContextBuilder,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> None:
        self._llm = llm
        self._context = context_builder
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _messages(
        self, question: str, context: BuiltContext, history: list[Message]
    ) -> list[LLMMessage]:
        rendered_history = self._context.render_history(history) if history else None
        return [
            LLMMessage(role="system", content=RAG_SYSTEM),
            LLMMessage(
                role="user",
                content=build_rag_prompt(question, context.text, rendered_history),
            ),
        ]

    async def generate(
        self,
        question: str,
        chunks: list[ScoredChunk],
        history: list[Message] | None = None,
    ) -> GeneratedAnswer:
        context = self._context.build(chunks)
        if context.is_empty:
            return GeneratedAnswer(text=REFUSAL_TEXT, grounded=False)

        result = await self._llm.complete(
            self._messages(question, context, history or []),
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        text = result.text.strip()
        if INSUFFICIENT_MARKER in text.upper():
            return GeneratedAnswer(
                text=REFUSAL_TEXT,
                provider=result.provider,
                model=result.model,
                usage=result.usage,
                grounded=False,
            )

        text = strip_invalid_markers(text, len(context.used))
        citations = build_citations(text, context.used)
        if not citations:
            # The model answered without markers; surface the passages it saw
            # so the user can still verify the claim.
            citations = fallback_citations(context.used)

        return GeneratedAnswer(
            text=text,
            citations=citations,
            provider=result.provider,
            model=result.model,
            usage=result.usage,
        )

    async def stream(
        self,
        question: str,
        chunks: list[ScoredChunk],
        history: list[Message] | None = None,
    ) -> AsyncIterator[tuple[str, str | None]]:
        """Yield (event_type, payload) pairs: ('delta', text) then ('done', None)."""
        context = self._context.build(chunks)
        if context.is_empty:
            yield "delta", REFUSAL_TEXT
            yield "done", None
            return

        buffer: list[str] = []
        async for delta in self._llm.stream(
            self._messages(question, context, history or []),
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        ):
            buffer.append(delta)
            yield "delta", delta

        full = "".join(buffer).strip()
        if INSUFFICIENT_MARKER in full.upper():
            yield "delta", "\n\n" + REFUSAL_TEXT
        yield "done", None

    def citations_for(self, answer: str, chunks: list[ScoredChunk]) -> list[Citation]:
        """Resolve citations after a stream has completed."""
        context = self._context.build(chunks)
        return build_citations(answer, context.used) or fallback_citations(context.used)
