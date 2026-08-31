"""Ordered LLM router: try each provider in turn, guarded by a circuit breaker."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from app.core import events
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.llm.base import (
    LLMClient,
    LLMError,
    LLMMessage,
    LLMResult,
    ProviderUnavailableError,
)
from app.llm.circuit_breaker import CircuitBreaker, CircuitOpenError

if TYPE_CHECKING:
    # Type-only: this module is imported by the composition root, and a runtime
    # import of Settings here would tie the provider chain to the settings
    # module for no benefit at run time.
    from app.core.config import Settings

logger = get_logger(__name__)


class AllProvidersFailedError(RuntimeError):
    def __init__(self, errors: dict[str, str]) -> None:
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        super().__init__(f"All LLM providers failed ({detail})")
        self.errors = errors


class FallbackLLM(LLMClient):
    """Presents a list of providers as one client.

    A non-retryable error (bad request, invalid key) fails fast for that
    provider but still moves on to the next; a healthy provider should not be
    blocked by a peer's misconfiguration.
    """

    name = "fallback"

    def __init__(
        self,
        clients: list[LLMClient],
        fail_threshold: int = 3,
        reset_seconds: float = 60.0,
    ) -> None:
        if not clients:
            raise ValueError("FallbackLLM requires at least one provider.")
        self._clients = clients
        self._breakers = {
            client.name: CircuitBreaker(client.name, fail_threshold, reset_seconds)
            for client in clients
        }
        self._last_used = clients[0].name

    @property
    def model(self) -> str:
        return self._clients[0].model

    @property
    def providers(self) -> list[str]:
        return [client.name for client in self._clients]

    def breaker_states(self) -> list[dict[str, object]]:
        return [breaker.snapshot() for breaker in self._breakers.values()]

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        errors: dict[str, str] = {}

        for index, client in enumerate(self._clients):
            breaker = self._breakers[client.name]
            try:
                await breaker.ensure_allowed()
            except CircuitOpenError as exc:
                errors[client.name] = str(exc)
                metrics.increment("llm_skipped_total", provider=client.name, reason="circuit_open")
                continue

            # "primary" is a position, not a name: it is the first provider that
            # was actually *tried*, so a fallback rate stays meaningful when the
            # preferred provider is skipped for want of a credential.
            role = "primary" if index == 0 else "fallback"
            metrics.increment("llm_requests_total", provider=client.name, role=role)

            try:
                result = await client.complete(messages, temperature, max_tokens)
            except Exception as exc:
                await breaker.record_failure()
                errors[client.name] = str(exc)
                metrics.increment("llm_errors_total", provider=client.name)
                logger.warning(
                    events.LLM_FAILED,
                    extra={
                        "event": events.LLM_FAILED,
                        "provider": client.name,
                        "model": client.model,
                        "role": role,
                        "error_type": type(exc).__name__,
                    },
                )
                continue

            await breaker.record_success()
            if index > 0:
                # The number an operator alerts on: the primary is failing often
                # enough that answers are coming from a second choice.
                metrics.increment("llm_fallback_total", provider=client.name)
                logger.warning(
                    events.LLM_FALLBACK,
                    extra={
                        "event": events.LLM_FALLBACK,
                        "provider": client.name,
                        "model": client.model,
                        "skipped": index,
                    },
                )
            self._last_used = client.name
            return result

        raise AllProvidersFailedError(errors)

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        errors: dict[str, str] = {}

        for client in self._clients:
            breaker = self._breakers[client.name]
            try:
                await breaker.ensure_allowed()
            except CircuitOpenError as exc:
                errors[client.name] = str(exc)
                continue

            emitted = False
            try:
                async for delta in client.stream(messages, temperature, max_tokens):
                    emitted = True
                    yield delta
            except Exception as exc:
                await breaker.record_failure()
                errors[client.name] = str(exc)
                if emitted:
                    # Partial output already reached the client; switching now
                    # would splice two different answers together.
                    raise ProviderUnavailableError(
                        f"Stream interrupted: {exc}", client.name
                    ) from exc
                logger.warning(
                    "stream provider failed, falling back",
                    extra={"provider": client.name, "err": str(exc)},
                )
                continue

            await breaker.record_success()
            self._last_used = client.name
            return

        raise AllProvidersFailedError(errors)

    @property
    def last_used(self) -> str:
        return self._last_used

    async def health(self) -> bool:
        return any(breaker.state.value != "open" for breaker in self._breakers.values())

    async def close(self) -> None:
        for client in self._clients:
            try:
                await client.close()
            except Exception as exc:
                logger.debug("close failed", extra={"provider": client.name, "err": str(exc)})


def build_llm(settings: Settings) -> FallbackLLM:
    """Construct the provider chain from settings, skipping unconfigured ones."""
    from app.llm.providers.gemini import GeminiClient
    from app.llm.providers.groq import GroqClient
    from app.llm.providers.openai import OpenAIClient

    # The loop below only calls a factory once it has checked that provider's
    # key is set, but that check is in another scope, so each factory restates
    # it. `or ""` would be shorter and would turn a configuration mistake into
    # a 401 from the provider at the first question instead.
    def required(value: str | None, name: str) -> str:
        if not value:
            raise LLMError(f"{name} has no API key configured.", provider=name, retryable=False)
        return value

    factories = {
        "gemini": lambda: GeminiClient(
            api_key=required(settings.gemini_api_key, "gemini"),
            model=settings.gemini_model,
            timeout=settings.llm_timeout,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        ),
        "groq": lambda: GroqClient(
            api_key=required(settings.groq_api_key, "groq"),
            model=settings.groq_model,
            timeout=settings.llm_timeout,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        ),
        "openai": lambda: OpenAIClient(
            api_key=required(settings.openai_api_key, "openai"),
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            timeout=settings.llm_timeout,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        ),
    }
    keys = {
        "gemini": settings.gemini_api_key,
        "groq": settings.groq_api_key,
        "openai": settings.openai_api_key,
    }

    clients: list[LLMClient] = []
    for name in settings.llm_provider_order:
        if name not in factories:
            logger.warning("unknown provider in order", extra={"provider": name})
            continue
        if not keys.get(name):
            logger.info("provider skipped, no api key", extra={"provider": name})
            continue
        try:
            clients.append(factories[name]())
        except Exception as exc:
            logger.error("provider init failed", extra={"provider": name, "err": str(exc)})

    if not clients:
        raise LLMError(
            "No LLM provider configured. Set at least one of "
            "GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY.",
            provider="fallback",
            retryable=False,
        )

    logger.info("llm chain ready", extra={"providers": [c.name for c in clients]})
    return FallbackLLM(
        clients,
        fail_threshold=settings.breaker_fail_threshold,
        reset_seconds=settings.breaker_reset_seconds,
    )
