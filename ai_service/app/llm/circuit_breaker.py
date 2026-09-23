"""Async circuit breaker guarding each LLM provider."""

from __future__ import annotations

import asyncio
import time
from enum import StrEnum

from app.core import events
from app.core.logging import get_logger
from app.core.metrics import metrics

logger = get_logger(__name__)


class BreakerState(StrEnum):
    CLOSED = "closed"  # healthy, calls pass through
    OPEN = "open"  # failing, calls rejected immediately
    HALF_OPEN = "half_open"  # probing with a single trial call


class CircuitOpenError(RuntimeError):
    def __init__(self, name: str, retry_in: float) -> None:
        super().__init__(f"Circuit '{name}' is open; retry in {retry_in:.1f}s.")
        self.name = name
        self.retry_in = retry_in


class CircuitBreaker:
    """Stops hammering a provider that is already failing, and lets one probe
    through after the reset window to decide whether it has recovered."""

    def __init__(
        self,
        name: str,
        fail_threshold: int = 3,
        reset_seconds: float = 60.0,
        success_threshold: int = 1,
    ) -> None:
        self.name = name
        self._fail_threshold = fail_threshold
        self._reset_seconds = reset_seconds
        self._success_threshold = success_threshold
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._successes = 0
        self._opened_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> BreakerState:
        return self._state

    def _retry_in(self) -> float:
        return max(0.0, self._reset_seconds - (time.monotonic() - self._opened_at))

    async def allows(self) -> bool:
        async with self._lock:
            if self._state is BreakerState.OPEN:
                if self._retry_in() <= 0:
                    self._state = BreakerState.HALF_OPEN
                    self._successes = 0
                    metrics.increment(
                        "circuit_transitions_total", provider=self.name, to="half_open"
                    )
                    logger.info(
                        events.CIRCUIT_HALF_OPEN,
                        extra={
                            "event": events.CIRCUIT_HALF_OPEN,
                            "provider": self.name,
                            "failure_count": self._failures,
                        },
                    )
                    return True
                return False
            return True

    async def ensure_allowed(self) -> None:
        if not await self.allows():
            raise CircuitOpenError(self.name, self._retry_in())

    async def record_success(self) -> None:
        async with self._lock:
            if self._state is BreakerState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self._success_threshold:
                    self._reset_locked()
                    metrics.increment("circuit_transitions_total", provider=self.name, to="closed")
                    logger.info(
                        events.CIRCUIT_CLOSED,
                        extra={"event": events.CIRCUIT_CLOSED, "provider": self.name},
                    )
            else:
                self._failures = 0

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._state is BreakerState.HALF_OPEN or self._failures >= self._fail_threshold:
                self._state = BreakerState.OPEN
                self._opened_at = time.monotonic()
                metrics.increment("circuit_transitions_total", provider=self.name, to="open")
                # The provider's own error text is deliberately absent: it can
                # echo the request, and an opened circuit is diagnosed from the
                # failure count and the cooldown, not from the last message.
                logger.warning(
                    events.CIRCUIT_OPENED,
                    extra={
                        "event": events.CIRCUIT_OPENED,
                        "provider": self.name,
                        "failure_count": self._failures,
                        "cooldown_s": self._reset_seconds,
                    },
                )

    def _reset_locked(self) -> None:
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._successes = 0

    async def reset(self) -> None:
        async with self._lock:
            self._reset_locked()

    def snapshot(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self._state.value,
            "failures": self._failures,
            "retry_in": round(self._retry_in(), 1) if self._state is BreakerState.OPEN else 0.0,
        }
