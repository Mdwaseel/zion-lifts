import pytest

from app.llm.circuit_breaker import BreakerState, CircuitBreaker, CircuitOpenError


async def test_opens_after_threshold_failures():
    breaker = CircuitBreaker("test", fail_threshold=2, reset_seconds=60)
    await breaker.record_failure()
    assert breaker.state is BreakerState.CLOSED
    await breaker.record_failure()
    assert breaker.state is BreakerState.OPEN


async def test_open_circuit_rejects_calls():
    breaker = CircuitBreaker("test", fail_threshold=1, reset_seconds=60)
    await breaker.record_failure()
    with pytest.raises(CircuitOpenError):
        await breaker.ensure_allowed()


async def test_half_opens_after_reset_window():
    breaker = CircuitBreaker("test", fail_threshold=1, reset_seconds=0)
    await breaker.record_failure()
    assert await breaker.allows()
    assert breaker.state is BreakerState.HALF_OPEN


async def test_success_in_half_open_closes_circuit():
    breaker = CircuitBreaker("test", fail_threshold=1, reset_seconds=0)
    await breaker.record_failure()
    await breaker.allows()
    await breaker.record_success()
    assert breaker.state is BreakerState.CLOSED


async def test_failure_in_half_open_reopens():
    breaker = CircuitBreaker("test", fail_threshold=5, reset_seconds=0)
    await breaker.record_failure()
    breaker._state = BreakerState.HALF_OPEN
    await breaker.record_failure()
    assert breaker.state is BreakerState.OPEN


async def test_success_resets_failure_count():
    breaker = CircuitBreaker("test", fail_threshold=3, reset_seconds=60)
    await breaker.record_failure()
    await breaker.record_success()
    await breaker.record_failure()
    await breaker.record_failure()
    assert breaker.state is BreakerState.CLOSED
