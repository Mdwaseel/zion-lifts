"""Google Gemini provider via the google-genai SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.core.logging import get_logger
from app.llm.base import (
    LLMClient,
    LLMError,
    LLMMessage,
    LLMResult,
    LLMUsage,
    ProviderUnavailableError,
    RateLimitError,
    split_system,
)

logger = get_logger(__name__)

_ROLE_MAP = {"user": "user", "assistant": "model"}


class GeminiClient(LLMClient):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        timeout: float = 45.0,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._timeout = timeout
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    # Returns `Any` rather than `object`: the SDK's config type is only
    # importable inside this function, and the content dicts are a nested
    # literal structure no annotation here would describe usefully.
    def _prepare(
        self, messages: list[LLMMessage], temperature: float | None, max_tokens: int | None
    ) -> tuple[list[dict[str, Any]], Any]:
        from google.genai import types

        system, rest = split_system(messages)
        contents = [
            {"role": _ROLE_MAP.get(m.role, "user"), "parts": [{"text": m.content}]} for m in rest
        ]
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self._temperature if temperature is None else temperature,
            max_output_tokens=self._max_tokens if max_tokens is None else max_tokens,
        )
        return contents, config

    def _wrap(self, exc: Exception) -> LLMError:
        text = str(exc).lower()
        if "quota" in text or "429" in text or "resource_exhausted" in text:
            return RateLimitError(str(exc), self.name)
        if "api key" in text or "permission" in text or "401" in text:
            return LLMError(str(exc), self.name, retryable=False)
        return ProviderUnavailableError(str(exc), self.name)

    @staticmethod
    def _usage(response: object) -> LLMUsage:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return LLMUsage()
        return LLMUsage(
            prompt_tokens=getattr(meta, "prompt_token_count", None),
            completion_tokens=getattr(meta, "candidates_token_count", None),
            total_tokens=getattr(meta, "total_token_count", None),
        )

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        contents, config = self._prepare(messages, temperature, max_tokens)
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except Exception as exc:
            raise self._wrap(exc) from exc

        candidates = getattr(response, "candidates", None) or []
        return LLMResult(
            text=response.text or "",
            provider=self.name,
            model=self._model,
            usage=self._usage(response),
            finish_reason=str(getattr(candidates[0], "finish_reason", "")) if candidates else None,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        contents, config = self._prepare(messages, temperature, max_tokens)
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=self._model, contents=contents, config=config
            )
            async for event in stream:
                if event.text:
                    yield event.text
        except Exception as exc:
            raise self._wrap(exc) from exc
