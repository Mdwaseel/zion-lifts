"""Building the embedding provider this deployment is configured for.

One place, because two places would eventually disagree — and an API embedding
queries with one model while a worker indexes with another is a failure with no
error message: every search simply returns the wrong passages.

Two implementations sit behind this function. The API provider calls Hugging
Face over HTTP and needs nothing heavier than httpx; the local one loads
sentence-transformers, and therefore torch, into the process. Which one runs is
a configuration question (``EMBEDDING_PROVIDER``, defaulting to whichever the
environment can actually support), so no caller has to know — and, importantly,
the local module is imported lazily, because naming it at the top of this file
would make torch a hard requirement of an image built deliberately without it.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.embeddings.api_huggingface import HuggingFaceAPIEmbeddings
from app.embeddings.provider import EmbeddingProvider
from app.embeddings.router import EmbeddingRouter

logger = get_logger(__name__)


def _build_one(settings: Settings, model_name: str) -> EmbeddingProvider:
    """One provider for one model, of whichever kind is configured."""
    if settings.embeddings_use_api:
        return HuggingFaceAPIEmbeddings(
            model_name=model_name,
            # Non-null whenever `embeddings_use_api` is true: "api" without a
            # token is refused in Settings, and "auto" only resolves to the API
            # because a token is present.
            api_token=settings.hf_api_token or "",
            dimension=settings.embedding_dim,
            batch_size=settings.embedding_batch_size,
            cache_size=settings.embedding_cache_size,
            timeout=settings.hf_api_timeout,
            max_retries=settings.hf_api_max_retries,
            backoff=settings.hf_api_backoff,
            api_base=settings.hf_api_base,
        )

    # Imported here, not at module scope: this line pulls in torch.
    from app.embeddings.huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=model_name,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        cache_size=settings.embedding_cache_size,
    )


def build_embeddings(settings: Settings) -> EmbeddingProvider:
    """The primary model, wrapped in a router when a fallback is configured.

    Always a router when there is a fallback, even though the fallback is
    usually never called: it is the router that keeps ``model_name`` honest
    about which provider produced the last set of vectors, and the ingestion
    pipeline names its collection from exactly that.
    """
    logger.info(
        "building embeddings",
        extra={
            "source": "api" if settings.embeddings_use_api else "local",
            "model": settings.embedding_model,
        },
    )
    primary = _build_one(settings, settings.embedding_model)

    fallback_name = (settings.embedding_fallback_model or "").strip()
    if not fallback_name:
        return primary

    if fallback_name == settings.embedding_model:
        # A fallback identical to the primary is not a fallback; it would just
        # fail twice as slowly.
        logger.warning(
            "EMBEDDING_FALLBACK_MODEL matches EMBEDDING_MODEL; ignoring it",
            extra={"model": fallback_name},
        )
        return primary

    fallback = _build_one(settings, fallback_name)
    logger.info(
        "embedding fallback configured",
        extra={"primary": settings.embedding_model, "fallback": fallback_name},
    )
    return EmbeddingRouter(primary=primary, fallback=fallback)
