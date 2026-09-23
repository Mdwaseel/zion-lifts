"""The chat and provider paths actually emit what an operator alerts on.

Written against the metric names rather than the log text, because the names are
the contract a dashboard is built on: renaming ``chat_refusals_total`` breaks a
panel silently, and this is what turns that into a failing test.

Each test drives the real pipeline with stubbed collaborators, so what is
asserted is that the *production* call sites record — not that a helper can be
called directly.
"""

from __future__ import annotations

import pytest

from app.core.metrics import metrics
from app.rag.pipeline import RagPipeline
from app.retrieval.scope import RetrievalScope
from app.vectorstore.base import ScoredChunk


@pytest.fixture(autouse=True)
def clean_metrics():
    metrics.reset()
    yield
    metrics.reset()


def chunk(text: str = "the shaft width is 1100mm", score: float = 0.9) -> ScoredChunk:
    return ScoredChunk(
        id="pt-1",
        text=text,
        document_id="doc-1",
        score=score,
        metadata={"chunk_index": 0, "document_version_id": "ver-1"},
    )


class StubSearch:
    def __init__(self, chunks=None, error: Exception | None = None) -> None:
        self._chunks = chunks if chunks is not None else [chunk()]
        self._error = error
        self.last_timings = {"dense": 12.0, "sparse": 8.0, "rrf": 1.0}

    async def search(self, query, collection, filters=None, limit=None):
        if self._error:
            raise self._error
        return self._chunks


class StubReranker:
    async def rerank(self, query, chunks, top_k):
        return chunks[:top_k]


class Generated:
    def __init__(self) -> None:
        self.text = "The shaft is 1100mm wide."
        self.citations = [object()]
        self.provider = "gemini"
        self.model = "gemini-2.0-flash"
        from app.llm.base import LLMUsage

        self.usage = LLMUsage()


class StubGenerator:
    def __init__(self, error: Exception | None = None, deltas=("Hello", " world")) -> None:
        self._error = error
        self._deltas = deltas

    async def generate(self, question, chunks, history):
        if self._error:
            raise self._error
        return Generated()

    async def stream(self, question, chunks, history):
        if self._error:
            raise self._error
        for delta in self._deltas:
            yield "delta", delta
        yield "done", None

    def citations_for(self, text, chunks):
        return [object()]


class StubRewriter:
    async def rewrite(self, question, history):
        return question


def build(search=None, generator=None, **kwargs) -> RagPipeline:
    return RagPipeline(
        search=search or StubSearch(),
        reranker=StubReranker(),
        generator=generator or StubGenerator(),
        rewriter=StubRewriter(),
        embedding_model="m",
        embedding_model_version="v1",
        **kwargs,
    )


SCOPE = RetrievalScope.legacy("documents")


class TestChatSuccess:
    async def test_a_successful_answer_is_counted(self):
        await build().ask("how wide is the shaft?", SCOPE)
        assert metrics.counter("chat_requests_total", mode="sync") == 1
        assert metrics.counter("chat_success_total", mode="sync") == 1
        assert metrics.counter("chat_errors_total", mode="sync") == 0

    async def test_every_stage_is_timed(self):
        result = await build().ask("how wide is the shaft?", SCOPE)
        fields = result.timings.as_log_fields()

        # The breakdown an operator uses to find *which* stage is slow.
        for stage in (
            "scope_resolution_ms",
            "query_rewrite_ms",
            "dense_retrieval_ms",
            "sparse_retrieval_ms",
            "rrf_ms",
            "reranking_ms",
            "grounding_ms",
            "total_ms",
        ):
            assert stage in fields, f"{stage} is not measured"
        # Present rather than positive: `as_log_fields` omits a stage that did
        # not run, so presence is what proves the model was actually reached.
        # A stub answers in well under a rounded millisecond.
        assert "llm_total_ms" in fields
        assert result.timings.llm_total_ms is not None
        assert result.timings.total_ms >= result.timings.grounding_ms

    async def test_the_retriever_timings_are_carried_through(self):
        # Read back from the searcher, which is the only thing that can tell
        # two concurrent retrievers apart.
        result = await build(search=StubSearch()).ask("q", SCOPE)
        assert result.timings.dense_retrieval_ms == 12.0
        assert result.timings.sparse_retrieval_ms == 8.0
        assert result.timings.rrf_ms == 1.0


class TestRefusal:
    """A refusal is the system working, and is counted apart from an error."""

    async def test_a_refusal_is_counted_as_a_refusal_not_a_failure(self):
        # No chunks -> nothing to ground an answer in.
        await build(search=StubSearch(chunks=[])).ask("q", SCOPE)

        assert metrics.counter("chat_refusals_total", mode="sync") == 1
        assert metrics.counter("grounding_refusal_total", mode="sync") == 1
        assert metrics.counter("chat_errors_total", mode="sync") == 0
        assert metrics.counter("chat_success_total", mode="sync") == 0

    async def test_a_refusal_never_reaches_the_model(self):
        generator = StubGenerator(error=AssertionError("the model must not be called"))
        result = await build(search=StubSearch(chunks=[]), generator=generator).ask("q", SCOPE)
        assert result.timings.llm_total_ms is None

    async def test_an_answered_request_counts_a_grounding_pass(self):
        await build().ask("q", SCOPE)
        assert metrics.counter("grounding_pass_total", mode="sync") == 1


class TestFailurePaths:
    async def test_a_retrieval_failure_is_counted_and_re_raised(self):
        pipeline = build(search=StubSearch(error=RuntimeError("qdrant down")))
        with pytest.raises(RuntimeError):
            await pipeline.ask("q", SCOPE)
        assert metrics.counter("retrieval_errors_total", stage="search") == 1

    async def test_a_generation_failure_is_counted_as_a_chat_error(self):
        pipeline = build(generator=StubGenerator(error=RuntimeError("all providers down")))
        with pytest.raises(RuntimeError):
            await pipeline.ask("q", SCOPE)
        assert metrics.counter("chat_errors_total", mode="sync") == 1
        assert metrics.counter("chat_success_total", mode="sync") == 0


class TestStreaming:
    async def _drain(self, pipeline):
        return [event async for event in pipeline.ask_stream("q", SCOPE)]

    async def test_time_to_first_token_is_measured(self):
        pipeline = build()
        await self._drain(pipeline)
        histogram = metrics.histogram("llm_time_to_first_token")
        assert histogram is not None and histogram.count == 1

    async def test_a_completed_stream_counts_as_a_success(self):
        await self._drain(build())
        assert metrics.counter("chat_success_total", mode="stream") == 1
        assert metrics.counter("chat_requests_total", mode="stream") == 1

    async def test_a_stream_that_never_yields_is_not_a_success(self):
        # An HTTP 200 is not evidence a stream worked: the status is sent before
        # a single token exists.
        pipeline = build(generator=StubGenerator(error=RuntimeError("provider died")))
        with pytest.raises(RuntimeError):
            await self._drain(pipeline)
        assert metrics.counter("chat_success_total", mode="stream") == 0
        assert metrics.counter("chat_errors_total", mode="stream") == 1

    async def test_a_client_disconnect_is_not_an_error(self):
        """A closed tab must not put a floor under the error rate."""
        pipeline = build()
        stream = pipeline.ask_stream("q", SCOPE)
        await stream.__anext__()  # take the first delta, then walk away
        await stream.aclose()

        assert metrics.counter("chat_stream_cancelled_total") == 1
        assert metrics.counter("chat_errors_total", mode="stream") == 0

    async def test_a_refused_stream_is_counted_as_a_refusal(self):
        await self._drain(build(search=StubSearch(chunks=[])))
        assert metrics.counter("chat_refusals_total", mode="stream") == 1


class TestProviderFallback:
    async def test_an_embedding_fallback_is_counted(self):
        from app.embeddings.router import EmbeddingRouter
        from tests.conftest import FakeEmbeddings

        class Failing(FakeEmbeddings):
            @property
            def model_name(self):
                return "primary/model"

            async def embed_documents(self, texts):
                raise RuntimeError("primary unavailable")

        class Working(FakeEmbeddings):
            @property
            def model_name(self):
                return "fallback/model"

        await EmbeddingRouter(primary=Failing(), fallback=Working()).embed_documents(["t"])

        assert metrics.counter("embedding_fallback_total") == 1
        assert metrics.counter("embedding_failures_total", role="primary") == 1
        assert metrics.counter("embedding_requests_total", role="fallback") == 1

    async def test_an_llm_fallback_is_counted_with_its_provider(self):
        from app.llm.base import LLMMessage, LLMResult, LLMUsage
        from app.llm.fallback import FallbackLLM

        class Provider:
            def __init__(self, name: str, fails: bool) -> None:
                self.name = name
                self.model = f"{name}-model"
                self._fails = fails

            async def complete(self, messages, temperature=None, max_tokens=None):
                if self._fails:
                    raise RuntimeError(f"{self.name} is down")
                return LLMResult(text="ok", provider=self.name, model=self.model, usage=LLMUsage())

            async def close(self):
                return None

        chain = FallbackLLM([Provider("gemini", True), Provider("groq", False)])
        await chain.complete([LLMMessage(role="user", content="hi")])

        assert metrics.counter("llm_fallback_total", provider="groq") == 1
        assert metrics.counter("llm_errors_total", provider="gemini") == 1
        assert metrics.counter("llm_requests_total", provider="gemini", role="primary") == 1
        assert metrics.counter("llm_requests_total", provider="groq", role="fallback") == 1

    async def test_a_circuit_opening_is_recorded(self):
        from app.llm.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker("gemini", fail_threshold=2)
        await breaker.record_failure()
        await breaker.record_failure()

        assert breaker.state.value == "open"
        assert metrics.counter("circuit_transitions_total", provider="gemini", to="open") == 1


class TestNoIdentifiersLeakIntoLabels:
    async def test_a_whole_chat_produces_no_high_cardinality_series(self):
        """The guard that keeps a dashboard from becoming a million charts."""
        await build().ask("how wide is the shaft?", SCOPE)
        snapshot = metrics.snapshot()

        forbidden = ("request_id=", "document_id=", "job_id=", "user_id=", "collection=")
        for key in list(snapshot["counters"]) + list(snapshot["histograms"]):
            assert not any(bad in key for bad in forbidden), key
        assert snapshot["meta"]["rejected_labels"] == 0
