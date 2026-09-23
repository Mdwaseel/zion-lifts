"""Embeddings from the Hugging Face Serverless Inference API.

The local provider next door loads sentence-transformers, which pulls in torch:
roughly 2.5 GB of wheels and a several-second import, carried by every API
container and every Celery worker child even though embedding is a few hundred
floats of arithmetic per chunk. This provider trades that for an HTTP call.

Three things about it are load-bearing and worth stating rather than
rediscovering:

*Normalisation is not optional.* The local provider encodes with
``normalize_embeddings=True``, so every vector already in Qdrant is unit length
and every collection is scored on that assumption. The API returns raw pooled
vectors. Skipping the L2 pass here would not raise anything — it would quietly
rank passages by magnitude as much as by direction, which is the class of
failure this codebase already goes to some trouble to avoid (see
``app/embeddings/router.py``). So it happens here, on every vector, before
anything else sees it.

*The width is discovered, not assumed.* ``dimension`` seeds from configuration
because the composition root reads it during start-up to create a collection,
before any text has been embedded. ``load()`` then spends one short request
confirming it against the model the token actually reaches, and corrects it if
they disagree — a collection created at the wrong width rejects every upsert
afterwards.

*A cold model is not an error.* The serverless API answers 503 while a model is
loaded onto a worker, for as long as a minute after a quiet period. That is the
normal first request of the day, not a failure, so it is retried with backoff
rather than raised.
"""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any

import httpx

from app.core import events
from app.core.errors import EmbeddingFailed, InvalidConfiguration
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.embeddings.cache import EmbeddingCache, cache_key
from app.embeddings.provider import EmbeddingProvider

logger = get_logger(__name__)

# The serverless inference host, and not the one most documentation still shows.
# `api-inference.huggingface.co` — the `/pipeline/feature-extraction/{model}`
# form — has been retired and no longer resolves at all: it fails DNS, so the
# symptom is a connection error rather than a 404, and it looks like a network
# problem rather than a wrong URL. Requests now go through the router, which
# takes the model first and the pipeline after it.
DEFAULT_API_BASE = "https://router.huggingface.co/hf-inference/models"
_PIPELINE = "pipeline/feature-extraction"

# Worth trying again: a cold model, a rate limit, a gateway hiccup. Anything
# else (400, 401, 404) means the request or the token is wrong, and the same
# call will be just as wrong in thirty seconds.
_RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})

# What the probe in `load()` embeds. Short on purpose: it exists to measure the
# width of the result, not to be a useful vector.
_PROBE_TEXT = "dimension probe"


def _l2_normalize(vector: list[float]) -> list[float]:
    """Scale to unit length, leaving a zero vector alone.

    A zero vector has no direction to preserve, and dividing by its norm would
    produce NaNs — which Qdrant accepts and no distance function survives.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0 or not math.isfinite(norm):
        return vector
    return [value / norm for value in vector]


def _mean_pool(token_vectors: list[list[float]]) -> list[float]:
    """Average token embeddings into one sentence embedding.

    Only reached for models whose feature-extraction pipeline returns per-token
    output instead of a pooled sentence vector. Mean pooling is what
    sentence-transformers itself applies to the MiniLM family, so this keeps the
    two providers producing comparable vectors for the same model.
    """
    if not token_vectors:
        raise EmbeddingFailed("the embedding API returned an empty token sequence")
    width = len(token_vectors[0])
    totals = [0.0] * width
    for token in token_vectors:
        if len(token) != width:
            raise EmbeddingFailed("the embedding API returned ragged token vectors")
        for i, value in enumerate(token):
            totals[i] += value
    count = float(len(token_vectors))
    return [total / count for total in totals]


class HuggingFaceAPIEmbeddings(EmbeddingProvider):
    """Text -> dense vector over HTTP, with the same contract as the local one.

    Safe to call concurrently: the httpx client is created once behind a lock
    and is itself concurrency-safe, and the cache takes its own.
    """

    def __init__(
        self,
        model_name: str,
        api_token: str,
        dimension: int = 384,
        batch_size: int = 32,
        cache_size: int = 4096,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff: float = 1.0,
        normalize: bool = True,
        api_base: str = DEFAULT_API_BASE,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_token:
            # Refused here rather than at the first request: an unauthenticated
            # serverless call fails per-chunk, halfway through an ingestion run,
            # instead of at start-up where it is one clear line in the log.
            raise InvalidConfiguration(
                "HF_API_TOKEN is required to embed through the Hugging Face API"
            )
        self._model_name = model_name
        self._api_token = api_token
        self._dimension = dimension
        self._batch_size = max(1, batch_size)
        self._timeout = timeout
        self._max_retries = max(0, max_retries)
        self._backoff = backoff
        self._normalize = normalize
        self._api_base = api_base.rstrip("/")
        self._cache = EmbeddingCache(cache_size)
        self._client = client
        self._owns_client = client is None
        self._client_lock = asyncio.Lock()
        self._probed = False
        self._probe_lock = asyncio.Lock()

    # --- identity ------------------------------------------------------------

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def endpoint(self) -> str:
        return f"{self._api_base}/{self._model_name}/{_PIPELINE}"

    # --- transport -----------------------------------------------------------

    async def _http(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self._timeout)
                self._owns_client = True
        return self._client

    def _headers(self) -> dict[str, str]:
        # Assembled per request and never logged.
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    async def _post(self, batch: list[str]) -> list[list[float]]:
        """One batch, retried while the failure still looks temporary."""
        client = await self._http()
        payload = {
            "inputs": batch,
            # `wait_for_model` turns a cold start into a slow response rather
            # than a 503 the caller would have to interpret.
            "options": {"wait_for_model": True, "use_cache": True},
        }

        last_error = "no attempt was made"
        for attempt in range(self._max_retries + 1):
            try:
                response = await client.post(self.endpoint, json=payload, headers=self._headers())
            except httpx.HTTPError as exc:
                # Transport-level: a timeout, a reset connection, DNS. Always
                # worth one more try.
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    return self._coerce(response.json(), len(batch))

                # `response.text` is the API's own message ("Model is currently
                # loading", "Rate limit reached"). It never echoes the request,
                # so it is safe to carry into a log; it is truncated because a
                # stray HTML error page should not become a kilobyte of it.
                detail = response.text[:300]
                if response.status_code in (401, 403):
                    raise InvalidConfiguration(
                        f"the Hugging Face API rejected the token for {self._model_name} "
                        f"(HTTP {response.status_code}); check HF_API_TOKEN and its read "
                        "permission on the model"
                    )
                if response.status_code == 404:
                    raise InvalidConfiguration(
                        "the Hugging Face API has no feature-extraction endpoint for "
                        f"{self._model_name} (HTTP 404); check EMBEDDING_MODEL"
                    )
                if response.status_code not in _RETRYABLE_STATUS:
                    raise EmbeddingFailed(
                        f"the embedding API returned HTTP {response.status_code} for "
                        f"{self._model_name}: {detail}"
                    )
                last_error = f"HTTP {response.status_code}: {detail}"

            if attempt < self._max_retries:
                metrics.increment("embedding_retries_total", source="api")
                delay = self._backoff * (2**attempt)
                logger.warning(
                    "embedding API call failed, retrying",
                    extra={
                        "model": self._model_name,
                        "attempt": attempt + 1,
                        "of": self._max_retries,
                        "delay_s": delay,
                        "err": last_error,
                    },
                )
                await asyncio.sleep(delay)

        raise EmbeddingFailed(
            f"the embedding API did not answer for {self._model_name} after "
            f"{self._max_retries + 1} attempts: {last_error}"
        )

    def _coerce(self, payload: Any, expected: int) -> list[list[float]]:
        """The response body as one vector per input, normalised.

        The feature-extraction pipeline answers with a 2-D array for models that
        pool internally and a 3-D one for models that do not, so both shapes are
        accepted and only the count is insisted on: a batch that came back short
        would otherwise slide every following chunk onto the wrong text.
        """
        # A dict here is the API's error envelope, not a result.
        if isinstance(payload, dict):
            message = str(payload.get("error", payload))[:300]
            raise EmbeddingFailed(f"the embedding API returned an error: {message}")
        if not isinstance(payload, list) or not payload:
            raise EmbeddingFailed(
                f"the embedding API returned {type(payload).__name__}, not a list of vectors"
            )

        rows: list[list[float]] = []
        for row in payload:
            if not isinstance(row, list) or not row:
                raise EmbeddingFailed("the embedding API returned a malformed vector")
            if isinstance(row[0], list):
                rows.append(_mean_pool([[float(v) for v in token] for token in row]))
            else:
                rows.append([float(v) for v in row])

        if len(rows) != expected:
            raise EmbeddingFailed(
                f"the embedding API returned {len(rows)} vectors for {expected} inputs"
            )

        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise EmbeddingFailed("the embedding API returned vectors of differing widths")

        return [_l2_normalize(row) for row in rows] if self._normalize else rows

    # --- lifecycle -----------------------------------------------------------

    async def load(self) -> None:
        """Confirm the model's real width, once, before anything is indexed.

        Deliberately does not raise when the API cannot be reached. This runs at
        start-up, and a service that refuses to boot because a third-party HTTP
        endpoint was briefly unhappy is worse than one that boots on the
        configured width and reports the failure on the first real call.
        """
        if self._probed:
            return
        async with self._probe_lock:
            if self._probed:
                return
            try:
                vectors = await self._post([_PROBE_TEXT])
            except Exception as exc:
                logger.warning(
                    "could not confirm the embedding width from the API; "
                    "using the configured value",
                    extra={
                        "model": self._model_name,
                        "configured_dim": self._dimension,
                        "err": str(exc),
                    },
                )
                return

            self._probed = True
            measured = len(vectors[0])
            if measured != self._dimension:
                # Not fatal, and not to be swallowed either: the collection
                # about to be created takes its width from here.
                logger.warning(
                    "EMBEDDING_DIM does not match the model; using the model's width",
                    extra={
                        "model": self._model_name,
                        "configured": self._dimension,
                        "measured": measured,
                    },
                )
                self._dimension = measured
            self._cache.set(cache_key(self._model_name, _PROBE_TEXT), vectors[0])
            logger.info(
                "embedding API ready",
                extra={"model": self._model_name, "dim": self._dimension},
            )

    async def aclose(self) -> None:
        """Release the HTTP client, if this provider made one."""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    # --- embedding -----------------------------------------------------------

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        pending: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            cached = self._cache.get(cache_key(self._model_name, text))
            if cached is not None:
                results[i] = cached
            else:
                pending.append((i, text))

        batches = 0
        started = time.perf_counter()
        for start in range(0, len(pending), self._batch_size):
            window = pending[start : start + self._batch_size]
            mark = time.perf_counter()
            try:
                vectors = await self._post([text for _, text in window])
            except Exception:
                metrics.increment("embedding_errors_total", source="api")
                raise
            metrics.observe(
                "embedding_batch_duration", (time.perf_counter() - mark) * 1000, source="api"
            )
            batches += 1
            for (i, text), vector in zip(window, vectors, strict=True):
                results[i] = vector
                self._cache.set(cache_key(self._model_name, text), vector)

        if batches:
            metrics.increment("embedding_batches_total", value=batches, source="api")
            metrics.increment("embedding_vectors_total", value=len(pending), source="api")
            metrics.observe(
                "embedding_duration", (time.perf_counter() - started) * 1000, source="api"
            )
            logger.debug(
                events.EMBEDDING_COMPLETED,
                extra={
                    "event": events.EMBEDDING_COMPLETED,
                    # Counts and shapes. Never a vector, never a passage.
                    "model": self._model_name,
                    "requested": len(texts),
                    "embedded": len(pending),
                    "cached": len(texts) - len(pending),
                    "batches": batches,
                    "batch_size": self._batch_size,
                    "dimension": self._dimension,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )

        # Every slot is filled by construction. Raising rather than filtering
        # the Nones out keeps a short return from being mistaken for a
        # successful one — the caller zips these against chunk metadata.
        missing = [i for i, vector in enumerate(results) if vector is None]
        if missing:  # pragma: no cover - defensive
            raise EmbeddingFailed(f"{len(missing)} of {len(texts)} texts were not embedded")
        return [vector for vector in results if vector is not None]

    async def embed_query(self, text: str) -> list[float]:
        """Embed one query, in the same space as the indexed passages.

        Shares the batch path so a query gets the identical pooling, cache and
        normalisation the passages got. Anything else here would compare a
        question against the index in a slightly different geometry.
        """
        vectors = await self.embed_documents([text])
        return vectors[0]

    def cache_stats(self) -> dict[str, int | float]:
        return self._cache.stats()
