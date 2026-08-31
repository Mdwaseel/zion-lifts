"""Rewrite the user's question into a standalone retrieval query."""

from __future__ import annotations

import re

from app.api.schemas.chat import Message
from app.core.logging import get_logger
from app.llm.base import LLMClient, LLMMessage
from app.prompts.rewrite import REWRITE_SYSTEM, build_rewrite_prompt

logger = get_logger(__name__)

_FOLLOWUP_HINT = re.compile(
    r"\b(it|its|this|that|these|those|they|them|he|she|there|the same|instead|also)\b",
    re.IGNORECASE,
)
MAX_REWRITE_CHARS = 300


class QueryRewriter:
    """Follow-ups like "and what about pricing?" retrieve badly on their own.
    Rewriting folds the conversation back into a self-contained query."""

    def __init__(self, llm: LLMClient, enabled: bool = True) -> None:
        self._llm = llm
        self._enabled = enabled

    def needs_rewrite(self, question: str, history: list[Message]) -> bool:
        if not self._enabled or not history:
            return False
        return bool(_FOLLOWUP_HINT.search(question)) or len(question.split()) <= 6

    async def rewrite(self, question: str, history: list[Message]) -> str:
        if not self.needs_rewrite(question, history):
            return question
        try:
            result = await self._llm.complete(
                [
                    LLMMessage(role="system", content=REWRITE_SYSTEM),
                    LLMMessage(role="user", content=build_rewrite_prompt(question, history)),
                ],
                temperature=0.0,
                max_tokens=120,
            )
            rewritten = result.text.strip().strip('"').splitlines()[0].strip()
        except Exception as exc:
            logger.warning("query rewrite failed", extra={"err": str(exc)})
            return question

        if not rewritten or len(rewritten) > MAX_REWRITE_CHARS:
            return question
        logger.debug("query rewritten", extra={"original": question, "rewritten": rewritten})
        return rewritten
