"""Provider-agnostic LLM contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class LLMMessage:
    role: Role
    content: str


@dataclass(slots=True)
class LLMUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(slots=True)
class LLMResult:
    text: str
    provider: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    finish_reason: str | None = None


class LLMError(RuntimeError):
    """Base class for provider failures."""

    def __init__(self, message: str, provider: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class RateLimitError(LLMError):
    pass


class ProviderUnavailableError(LLMError):
    pass


class LLMClient(ABC):
    name: str = "base"

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult: ...

    @abstractmethod
    def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]: ...

    async def health(self) -> bool:
        return True

    async def close(self) -> None:  # pragma: no cover - optional override
        return None


def split_system(messages: list[LLMMessage]) -> tuple[str | None, list[LLMMessage]]:
    """Providers that take the system prompt as a separate argument need this."""
    system = "\n\n".join(m.content for m in messages if m.role == "system") or None
    rest = [m for m in messages if m.role != "system"]
    return system, rest
