"""Primary embedding model, with a fallback that cannot corrupt the index.

A fallback embedding model is not like a fallback LLM. If the primary language
model is down, the secondary answers and the only cost is a different voice. If
the primary *embedding* model is down, the secondary produces vectors in a
different space — geometrically unrelated to everything already indexed. Writing
them into the same collection does not degrade retrieval, it silently destroys
it: the new chunks sit at random distances from every query, and nothing
anywhere reports an error.

So the rule this class exists to enforce is narrow and absolute:

    the collection is named after the model that actually produced the vectors.

``active_model`` and ``dimension`` always describe the provider that answered
the most recent call, and the ingestion pipeline names its collection from
those — not from configuration, and not from the request. A fallback with a
different width therefore lands in a different collection, and the two never
meet.

For *queries* the rule bites differently, and harder: a query embedded by the
fallback cannot be compared against a collection built by the primary at all.
That is not a degraded answer, it is a meaningless one, so `embed_query` refuses
rather than falling back silently.
"""

from __future__ import annotations

from app.core import events
from app.core.errors import EmbeddingFailed
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.embeddings.provider import EmbeddingProvider

logger = get_logger(__name__)


class EmbeddingRouter(EmbeddingProvider):
    """Tries providers in order and reports which one answered.

    Not a load balancer: the first provider is used for everything until it
    fails. Spreading work across two embedding models would put two vector
    spaces in one collection, which is the exact failure this guards against.
    """

    def __init__(
        self,
        primary: EmbeddingProvider,
        fallback: EmbeddingProvider | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._active: EmbeddingProvider = primary
        self.fallback_events = 0

    # --- identity ------------------------------------------------------------

    @property
    def model_name(self) -> str:
        """The provider that answered last. This names the collection."""
        return self._active.model_name

    @property
    def dimension(self) -> int:
        return self._active.dimension

    @property
    def is_degraded(self) -> bool:
        return self._active is not self._primary

    @property
    def providers(self) -> list[str]:
        names = [self._primary.model_name]
        if self._fallback is not None:
            names.append(self._fallback.model_name)
        return names

    # --- embedding -----------------------------------------------------------

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages, falling back if the primary cannot.

        Safe to fall back here precisely because the caller reads
        ``model_name`` afterwards to decide where the vectors go. The pipeline
        does exactly that, so a fallback run writes to the fallback's own
        collection rather than contaminating the primary's.
        """
        if not texts:
            return []

        metrics.increment("embedding_requests_total", role="primary")
        try:
            vectors = await self._primary.embed_documents(texts)
        except Exception as primary_error:
            metrics.increment("embedding_failures_total", role="primary")
            if self._fallback is None:
                raise EmbeddingFailed(
                    f"{self._primary.model_name} failed and no fallback is configured: "
                    f"{primary_error}",
                    cause=primary_error,
                ) from primary_error

            self.fallback_events += 1
            metrics.increment("embedding_fallback_total")
            metrics.increment("embedding_requests_total", role="fallback")
            logger.warning(
                events.EMBEDDING_FALLBACK,
                extra={
                    "event": events.EMBEDDING_FALLBACK,
                    "primary": self._primary.model_name,
                    "fallback": self._fallback.model_name,
                    "error_type": type(primary_error).__name__,
                },
            )
            try:
                vectors = await self._fallback.embed_documents(texts)
            except Exception as fallback_error:
                metrics.increment("embedding_failures_total", role="fallback")
                raise EmbeddingFailed(
                    f"both embedding models failed — {self._primary.model_name}: "
                    f"{primary_error}; {self._fallback.model_name}: {fallback_error}",
                    cause=fallback_error,
                ) from fallback_error

            self._active = self._fallback
            return vectors

        # Recovering matters as much as failing over: a run pinned to the
        # fallback after one blip would keep writing to the wrong collection.
        if self._active is not self._primary:
            metrics.increment("embedding_recovered_total")
            logger.info(
                events.EMBEDDING_RECOVERED,
                extra={
                    "event": events.EMBEDDING_RECOVERED,
                    "primary": self._primary.model_name,
                },
            )
        self._active = self._primary
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        """Embed a search query. Never falls back.

        A query vector is only meaningful in the space the collection was built
        in. Answering with the fallback would compare a question in one geometry
        against passages in another and return whatever happened to be nearest —
        confidently, and wrongly. Failing is the correct outcome; the caller
        turns it into "search is unavailable".
        """
        try:
            vector = await self._primary.embed_query(text)
        except Exception as exc:
            metrics.increment("embedding_failures_total", role="primary", operation="query")
            raise EmbeddingFailed(
                f"cannot embed the query: {self._primary.model_name} is unavailable, and a "
                "fallback model's vectors are not comparable with the indexed ones",
                cause=exc,
            ) from exc

        self._active = self._primary
        return vector

    async def warmup(self) -> None:
        await self._primary.warmup()

    async def load(self) -> None:
        """Load the primary now; the fallback stays cold until it is needed.

        Loading both would double the resident memory of every worker child for
        a model that is usually never called.
        """
        await self._primary.load()
