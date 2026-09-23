"""The Hugging Face API embedding provider.

Every test here drives a mocked transport rather than the real endpoint: these
must fail because the provider is wrong, never because a third party is slow,
rate-limiting, or loading a model.

The properties worth defending are the ones whose failure is silent. A vector
that is not normalised still ranks, just wrongly. A batch that comes back short
still returns, just attached to the wrong chunks. Neither raises anything on its
own, so each gets a test.
"""

from __future__ import annotations

import json
import math

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import EmbeddingFailed, InvalidConfiguration
from app.embeddings.api_huggingface import HuggingFaceAPIEmbeddings
from app.embeddings.factory import build_embeddings
from app.embeddings.router import EmbeddingRouter

BARE = {"_env_file": None}
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOKEN = "hf_notarealtokenusedonlyintests"


def provider(handler, **kwargs) -> HuggingFaceAPIEmbeddings:
    """A provider wired to a mock transport, with retries off unless asked."""
    kwargs.setdefault("max_retries", 0)
    kwargs.setdefault("backoff", 0.001)
    return HuggingFaceAPIEmbeddings(
        model_name=MODEL,
        api_token=TOKEN,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        **kwargs,
    )


def vectors(count: int, width: int = 4, scale: float = 3.0):
    """`count` deliberately un-normalised vectors."""
    return [[scale * (i + 1), 0.0, 0.0, 0.0][:width] for i in range(count)]


def ok(payload):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return handler


class TestRequestShape:
    async def test_it_posts_to_the_feature_extraction_pipeline(self):
        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization")
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=vectors(1))

        await provider(handler).embed_documents(["a chunk"])

        # The router form. The older api-inference.huggingface.co host is
        # retired and does not resolve, so getting this wrong fails DNS and
        # reads like a network outage rather than a bad URL.
        assert seen["url"] == (
            "https://router.huggingface.co/hf-inference/models/"
            + MODEL
            + "/pipeline/feature-extraction"
        )
        assert seen["auth"] == f"Bearer {TOKEN}"
        assert seen["body"] == {
            "inputs": ["a chunk"],
            "options": {"wait_for_model": True, "use_cache": True},
        }

    async def test_a_missing_token_is_refused_at_construction(self):
        # Not at the first request, which would be halfway through an ingestion
        # run rather than at start-up.
        with pytest.raises(InvalidConfiguration):
            HuggingFaceAPIEmbeddings(model_name=MODEL, api_token="")

    async def test_no_texts_calls_nothing(self):
        def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
            raise AssertionError("the API was called for an empty list")

        assert await provider(handler).embed_documents([]) == []


class TestNormalisation:
    async def test_vectors_come_back_unit_length(self):
        """Everything already in Qdrant was written unit length by the local
        provider. An un-normalised vector here would rank by magnitude as much
        as by direction, and nothing would report it."""
        [vector] = await provider(ok(vectors(1, scale=7.0))).embed_documents(["text"])
        assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)

    async def test_queries_are_normalised_too(self):
        vector = await provider(ok(vectors(1, scale=11.0))).embed_query("a question")
        assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)

    async def test_a_zero_vector_survives_intact(self):
        # Dividing by a zero norm produces NaNs, which Qdrant accepts and no
        # distance function survives.
        [vector] = await provider(ok([[0.0, 0.0, 0.0, 0.0]])).embed_documents(["text"])
        assert vector == [0.0, 0.0, 0.0, 0.0]

    async def test_token_level_output_is_mean_pooled(self):
        # Models that do not pool internally answer with one vector per token.
        payload = [[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]]
        [vector] = await provider(ok(payload)).embed_documents(["text"])
        assert math.isclose(vector[0], vector[1])
        assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)


class TestBatching:
    async def test_texts_are_sent_in_batches_of_the_configured_size(self):
        batches: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            inputs = json.loads(request.content)["inputs"]
            batches.append(len(inputs))
            return httpx.Response(200, json=vectors(len(inputs)))

        result = await provider(handler, batch_size=2).embed_documents(["a", "b", "c", "d", "e"])

        assert batches == [2, 2, 1]
        assert len(result) == 5

    async def test_order_is_preserved_across_batches_and_the_cache(self):
        """The caller zips these against chunk metadata, so a reordering here
        attaches every citation to the wrong passage."""

        def handler(request: httpx.Request) -> httpx.Response:
            inputs = json.loads(request.content)["inputs"]
            # A distinct, recognisable vector per text.
            return httpx.Response(
                200, json=[[float(ord(text[0])), 0.0, 0.0, 1.0] for text in inputs]
            )

        embeddings = provider(handler, batch_size=2)
        first = await embeddings.embed_documents(["a", "b", "c"])
        # "b" is now cached; the others are not, which puts the cached hit in
        # the middle of a fresh batch.
        second = await embeddings.embed_documents(["x", "b", "y"])

        assert second[1] == first[1]
        assert second[0] != second[1] != second[2]

    async def test_a_repeated_text_is_not_sent_twice(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            inputs = json.loads(request.content)["inputs"]
            return httpx.Response(200, json=vectors(len(inputs)))

        embeddings = provider(handler)
        await embeddings.embed_documents(["same"])
        await embeddings.embed_documents(["same"])

        assert calls == 1
        assert embeddings.cache_stats()["hits"] == 1


class TestMalformedResponses:
    async def test_a_short_batch_is_refused(self):
        # Two texts, one vector. Returning it would slide every following chunk
        # onto the wrong text.
        with pytest.raises(EmbeddingFailed, match="1 vectors for 2 inputs"):
            await provider(ok(vectors(1))).embed_documents(["a", "b"])

    async def test_ragged_widths_are_refused(self):
        payload = [[1.0, 0.0], [1.0, 0.0, 0.0]]
        with pytest.raises(EmbeddingFailed, match="differing widths"):
            await provider(ok(payload)).embed_documents(["a", "b"])

    async def test_an_error_envelope_is_reported(self):
        payload = {"error": "Model is currently loading", "estimated_time": 20}
        with pytest.raises(EmbeddingFailed, match="Model is currently loading"):
            await provider(ok(payload)).embed_documents(["a"])


class TestFailureHandling:
    async def test_a_cold_model_is_retried_and_then_succeeds(self):
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(503, text="Model is currently loading")
            return httpx.Response(200, json=vectors(1))

        result = await provider(handler, max_retries=2, backoff=0.001).embed_documents(["text"])

        assert attempts == 2
        assert len(result) == 1

    async def test_retries_are_bounded(self):
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(503, text="still loading")

        with pytest.raises(EmbeddingFailed):
            await provider(handler, max_retries=2, backoff=0.001).embed_documents(["text"])
        assert attempts == 3  # the first try plus two retries

    async def test_a_rejected_token_is_a_configuration_error_not_a_retry(self):
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(401, text="Authorization header is invalid")

        with pytest.raises(InvalidConfiguration, match="HF_API_TOKEN"):
            await provider(handler, max_retries=3, backoff=0.001).embed_documents(["text"])
        assert attempts == 1

    async def test_an_unknown_model_is_a_configuration_error(self):
        with pytest.raises(InvalidConfiguration, match="EMBEDDING_MODEL"):
            await provider(lambda r: httpx.Response(404, text="Not Found")).embed_documents(["t"])

    async def test_a_transport_failure_is_reported_as_an_embedding_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("no route to host")

        with pytest.raises(EmbeddingFailed):
            await provider(handler).embed_documents(["text"])

    async def test_the_error_never_carries_the_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal error")

        with pytest.raises(EmbeddingFailed) as caught:
            await provider(handler).embed_documents(["text"])
        assert TOKEN not in str(caught.value)


class TestDimension:
    async def test_load_measures_the_real_width(self):
        embeddings = provider(ok(vectors(1, width=4)), dimension=384)
        await embeddings.load()
        assert embeddings.dimension == 4

    async def test_an_unreachable_api_does_not_stop_start_up(self):
        """`load()` runs during start-up. Refusing to boot because a third
        party was briefly unhappy is worse than booting on the configured width
        and reporting it on the first real call."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("unreachable")

        embeddings = provider(handler, dimension=384)
        await embeddings.load()
        assert embeddings.dimension == 384


class TestFactory:
    def test_a_token_selects_the_api_provider(self):
        built = build_embeddings(Settings(**BARE, hf_api_token=TOKEN))
        assert isinstance(built, HuggingFaceAPIEmbeddings)

    def test_no_token_leaves_the_local_provider(self):
        # Constructed, not loaded: instantiating the local provider does not
        # import torch, so this stays runnable in an image without it.
        built = build_embeddings(Settings(**BARE))
        assert not isinstance(built, HuggingFaceAPIEmbeddings)

    def test_api_without_a_token_is_refused_at_configuration(self):
        from app.core.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            Settings(**BARE, embedding_provider="api")

    def test_the_fallback_uses_the_same_transport_as_the_primary(self):
        # A router mixing an API primary with a local fallback would need torch
        # installed to survive its own failover.
        built = build_embeddings(
            Settings(**BARE, hf_api_token=TOKEN, embedding_fallback_model="BAAI/bge-small-en-v1.5")
        )
        assert isinstance(built, EmbeddingRouter)
        assert built.providers == [MODEL, "BAAI/bge-small-en-v1.5"]

    def test_the_hf_prefixed_model_name_binds_to_the_same_field(self):
        # The deployed .env writes HF_EMBEDDING_MODEL. Binding it to a second
        # field would let the two disagree about what the collection is named.
        settings = Settings(**BARE, hf_embedding_model="BAAI/bge-small-en-v1.5")
        assert settings.embedding_model == "BAAI/bge-small-en-v1.5"


class TestModelIdHygiene:
    """A model name is also a collection name, so it has to be exactly a name."""

    def test_an_uncommented_env_value_is_refused(self):
        # The failure this caught in a real .env: the line read
        #   HF_EMBEDDING_MODEL=some/model  # the primary
        # and the comment arrived attached to the value, which the API answered
        # 400 to on every call.
        from app.core.exceptions import ConfigurationError

        with pytest.raises((ConfigurationError, ValueError)):
            Settings(**BARE, embedding_model=f"{MODEL} # the primary")

    def test_surrounding_whitespace_is_trimmed(self):
        assert Settings(**BARE, embedding_model=f"  {MODEL}  ").embedding_model == MODEL
