"""Qdrant-backed implementation of the VectorStore contract."""

from __future__ import annotations

from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.core.logging import get_logger
from app.vectorstore.base import ScoredChunk, VectorRecord, VectorStore
from app.vectorstore.collections import (
    DOCUMENT_ID_FIELD,
    KEYWORD_INDEXES,
    TEXT_FIELD,
)

logger = get_logger(__name__)


def _to_filter(filters: dict[str, Any] | None) -> models.Filter | None:
    """Translate a flat `{field: value | [values]}` dict into a Qdrant filter."""
    if not filters:
        return None
    conditions: list[models.FieldCondition] = []
    for key, value in filters.items():
        if value is None:
            continue
        match = (
            models.MatchAny(any=list(value))
            if isinstance(value, (list, tuple, set))
            else models.MatchValue(value=value)
        )
        conditions.append(models.FieldCondition(key=key, match=match))
    return models.Filter(must=conditions) if conditions else None


def _to_chunk(point: Any, score: float) -> ScoredChunk:
    payload = dict(point.payload or {})
    return ScoredChunk(
        id=str(point.id),
        text=payload.pop(TEXT_FIELD, ""),
        document_id=payload.get(DOCUMENT_ID_FIELD, ""),
        score=score,
        metadata=payload,
    )


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = AsyncQdrantClient(url=url, api_key=api_key, timeout=int(timeout))
        self._ensured: set[str] = set()

    async def ensure_collection(self, name: str, vector_size: int) -> None:
        if name in self._ensured:
            return
        if not await self._client.collection_exists(name):
            await self._client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )
            logger.info("created collection", extra={"collection": name, "dim": vector_size})
            for field in KEYWORD_INDEXES:
                try:
                    await self._client.create_payload_index(
                        collection_name=name,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                except Exception as exc:  # index may already exist
                    logger.debug("payload index skipped", extra={"field": field, "err": str(exc)})
        self._ensured.add(name)

    async def upsert(self, collection: str, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        points = [
            models.PointStruct(
                id=record.id,
                vector=record.vector,
                payload={
                    TEXT_FIELD: record.text,
                    DOCUMENT_ID_FIELD: record.document_id,
                    **record.metadata,
                },
            )
            for record in records
        ]
        await self._client.upsert(collection_name=collection, points=points, wait=True)
        return len(points)

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        response = await self._client.query_points(
            collection_name=collection,
            query=vector,
            limit=top_k,
            query_filter=_to_filter(filters),
            with_payload=True,
        )
        return [_to_chunk(point, point.score) for point in response.points]

    async def scroll(
        self,
        collection: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: str | None = None,
    ) -> tuple[list[ScoredChunk], str | None]:
        points, next_offset = await self._client.scroll(
            collection_name=collection,
            scroll_filter=_to_filter(filters),
            limit=limit,
            offset=offset,
            with_payload=True,
        )
        return [_to_chunk(p, 0.0) for p in points], (
            str(next_offset) if next_offset is not None else None
        )

    async def delete_document(self, collection: str, document_id: str) -> int:
        selector = _to_filter({DOCUMENT_ID_FIELD: document_id})
        before = await self._count_filtered(collection, selector)
        await self._client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(filter=selector),
            wait=True,
        )
        return before

    async def count(self, collection: str) -> int:
        return await self._count_filtered(collection, None)

    async def _count_filtered(self, collection: str, flt: models.Filter | None) -> int:
        result = await self._client.count(
            collection_name=collection, count_filter=flt, exact=True
        )
        return int(result.count)

    async def health(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:
            logger.warning("qdrant health check failed", extra={"err": str(exc)})
            return False

    async def close(self) -> None:
        await self._client.close()
