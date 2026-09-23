"""OpenAI (and any OpenAI-compatible endpoint) chat provider."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.llm.base import (
    LLMClient,
    LLMError,
    LLMMessage,
    LLMResult,
    LLMUsage,
    ProviderUnavailableError,
    RateLimitError,
)

logger = get_logger(__name__)


class OpenAIClient(LLMClient):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        timeout: float = 45.0,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    def _payload(
        self, messages: list[LLMMessage], temperature: float | None, max_tokens: int | None
    ) -> dict[str, object]:
        return {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self._temperature if temperature is None else temperature,
            "max_tokens": self._max_tokens if max_tokens is None else max_tokens,
        }

    def _wrap(self, exc: Exception) -> LLMError:
        from openai import APIStatusError
        from openai import RateLimitError as OpenAIRateLimit

        if isinstance(exc, OpenAIRateLimit):
            return RateLimitError(str(exc), self.name)
        if isinstance(exc, APIStatusError) and 400 <= exc.status_code < 500:
            return LLMError(str(exc), self.name, retryable=False)
        return ProviderUnavailableError(str(exc), self.name)

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        try:
            response = await self._client.chat.completions.create(
                **self._payload(messages, temperature, max_tokens)
            )
        except Exception as exc:
            raise self._wrap(exc) from exc

        choice = response.choices[0]
        usage = response.usage
        return LLMResult(
            text=choice.message.content or "",
            provider=self.name,
            model=response.model,
            finish_reason=choice.finish_reason,
            usage=LLMUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            ),
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                stream=True, **self._payload(messages, temperature, max_tokens)
            )
            async for event in stream:
                if event.choices and (delta := event.choices[0].delta.content):
                    yield delta
        except Exception as exc:
            raise self._wrap(exc) from exc

    async def close(self) -> None:
        await self._client.close()
