"""Operator-only endpoints. Guarded by the internal token, never by API key."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import Container, get_container
from app.core.security import require_internal_token
from app.vectorstore.collections import resolve

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    include_in_schema=False,
    dependencies=[Depends(require_internal_token)],
)


@router.get("/stats", summary="Runtime and index statistics")
async def stats(
    collection: str | None = Query(None),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    settings = container.settings
    target = resolve(collection, settings.qdrant_collection)

    embeddings = container.embeddings
    cache = embeddings.cache_stats() if hasattr(embeddings, "cache_stats") else {}

    return {
        "collection": target,
        "chunk_count": await container.store.count(target),
        "embeddings": {
            "model": embeddings.model_name,
            "dimension": embeddings.dimension,
            "cache": cache,
        },
        "llm": {
            "providers": container.llm.providers,
            "last_used": container.llm.last_used,
            "circuits": container.llm.breaker_states(),
        },
        "retrieval": {
            "dense_top_k": settings.dense_top_k,
            "sparse_top_k": settings.sparse_top_k,
            "fusion_top_k": settings.fusion_top_k,
            "rerank_top_k": settings.rerank_top_k,
            "hybrid_alpha": settings.hybrid_alpha,
            "reranker": settings.reranker_model if settings.reranker_enabled else None,
            "query_rewrite": settings.query_rewrite_enabled,
            "min_retrieval_score": settings.min_retrieval_score,
            "min_rerank_score": settings.min_rerank_score,
            "confidence_bands": [settings.confidence_low, settings.confidence_high],
            "max_context_tokens": settings.max_context_tokens,
        },
    }


@router.post("/circuits/reset", summary="Force all LLM circuit breakers closed")
async def reset_circuits(container: Container = Depends(get_container)) -> dict[str, Any]:
    for breaker in container.llm._breakers.values():  # noqa: SLF001 - operator escape hatch
        await breaker.reset()
    return {"reset": True, "circuits": container.llm.breaker_states()}


@router.post("/cache/clear", summary="Drop the in-process embedding cache")
async def clear_cache(container: Container = Depends(get_container)) -> dict[str, Any]:
    cache = getattr(container.embeddings, "_cache", None)
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="The active embedding provider has no cache.",
        )
    cache.clear()
    return {"cleared": True}


@router.post("/collections/ensure", summary="Create a collection if it is missing")
async def ensure_collection(
    name: str = Query(..., min_length=1),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    await container.store.ensure_collection(name, container.embeddings.dimension)
    return {"collection": name, "chunk_count": await container.store.count(name)}
