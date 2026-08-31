import pytest

from app.llm.base import LLMMessage
from app.llm.fallback import AllProvidersFailedError, FallbackLLM
from tests.conftest import FakeLLM

MESSAGES = [LLMMessage(role="user", content="hi")]


async def test_first_healthy_provider_wins():
    primary, secondary = FakeLLM("from primary"), FakeLLM("from secondary")
    result = await FallbackLLM([primary, secondary]).complete(MESSAGES)
    assert result.text == "from primary"
    assert secondary.calls == 0


async def test_falls_through_to_the_next_provider():
    broken, healthy = FakeLLM(fail=True), FakeLLM("recovered")
    result = await FallbackLLM([broken, healthy]).complete(MESSAGES)
    assert result.text == "recovered"


async def test_raises_when_every_provider_fails():
    llm = FallbackLLM([FakeLLM(fail=True), FakeLLM(fail=True)])
    with pytest.raises(AllProvidersFailedError) as exc:
        await llm.complete(MESSAGES)
    assert len(exc.value.errors) == 2


async def test_breaker_opens_and_stops_calling_a_dead_provider():
    broken, healthy = FakeLLM(fail=True), FakeLLM("ok")
    llm = FallbackLLM([broken, healthy], fail_threshold=2, reset_seconds=60)

    for _ in range(3):
        await llm.complete(MESSAGES)

    assert broken.calls == 2  # stopped once the circuit opened
    assert healthy.calls == 3


async def test_streaming_falls_back_before_any_output():
    llm = FallbackLLM([FakeLLM(fail=True), FakeLLM("hello world")])
    chunks = [c async for c in llm.stream(MESSAGES)]
    assert "".join(chunks).strip() == "hello world"


async def test_requires_at_least_one_provider():
    with pytest.raises(ValueError):
        FallbackLLM([])
