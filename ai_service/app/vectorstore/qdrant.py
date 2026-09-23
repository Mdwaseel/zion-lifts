"""Qdrant-backed implementation of the VectorStore contract."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.core import events
from app.core.errors import VectorStoreUnavailable
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.vectorstore.base import ScoredChunk, SparseVector, VectorRecord, VectorStore
from app.vectorstore.collections import (
    BOOL_INDEXES,
    DENSE_VECTOR,
    DOCUMENT_ID_FIELD,
    KEYWORD_INDEXES,
    SPARSE_VECTOR,
    TEXT_FIELD,
)

logger = get_logger(__name__)

# Which vector layout a collection uses. Named is what this version creates;
# legacy is one unnamed dense vector, created before Phase 4 and still readable.
_NAMED = "named"
_LEGACY = "legacy"


def _conditions(filters: dict[str, Any] | None) -> list[models.FieldCondition]:
    conditions: list[models.FieldCondition] = []
    for key, value in (filters or {}).items():
        if value is None:
            continue
        match = (
            models.MatchAny(any=list(value))
            if isinstance(value, (list, tuple, set))
            else models.MatchValue(value=value)
        )
        conditions.append(models.FieldCondition(key=key, match=match))
    return conditions


def _to_filter(
    filters: dict[str, Any] | None, exclude: dict[str, Any] | None = None
) -> models.Filter | None:
    """Translate flat `{field: value | [values]}` dicts into a Qdrant filter.

    ``exclude`` becomes ``must_not``, which is what "everything for this
    document except the version that just landed" needs.
    """
    must = _conditions(filters)
    must_not = _conditions(exclude)
    if not must and not must_not:
        return None
    # Sequence, not list: models.Filter accepts a union of condition types and
    # list is invariant, so a list[FieldCondition] is not a list[<union>].
    return models.Filter(must=list(must), must_not=list(must_not) or None)


def _to_chunk(point: Any, score: float) -> ScoredChunk:
    payload = dict(point.payload or {})
    return ScoredChunk(
        id=str(point.id),
        text=payload.pop(TEXT_FIELD, ""),
        document_id=payload.get(DOCUMENT_ID_FIELD, ""),
        score=score,
        metadata=payload,
    )


@asynccontextmanager
async def _observed(operation: str) -> AsyncIterator[None]:
    """Time one Qdrant call and count how it ended.

    Wrapped around each operation rather than pushed into the client so that
    the label is the *logical* operation — "upsert", "dense_search" — and not
    the HTTP method, which is the same for all of them and therefore useless
    for telling which one is slow.

    The collection name is never a label: there is one per knowledge base per
    embedding model, which is exactly the unbounded growth metric labels must
    not have. It stays in the log line.
    """
    mark = time.perf_counter()
    try:
        yield
    except Exception as exc:
        took = (time.perf_counter() - mark) * 1000
        metrics.observe("qdrant_operation_duration", took, operation=operation, status="error")
        metrics.increment("qdrant_errors_total", operation=operation)
        # A timeout and a refused connection are different incidents with
        # different runbooks, so the class of failure is recorded even though
        # the message is not.
        if "timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower()[:200]:
            metrics.increment("qdrant_timeouts_total", operation=operation)
        logger.warning(
            events.DEPENDENCY_UNAVAILABLE,
            extra={
                "event": events.DEPENDENCY_UNAVAILABLE,
                "dependency": "qdrant",
                "operation": operation,
                "error_type": type(exc).__name__,
                "duration_ms": round(took, 1),
            },
        )
        raise
    took = (time.perf_counter() - mark) * 1000
    metrics.observe("qdrant_operation_duration", took, operation=operation, status="ok")
    metrics.increment("qdrant_operations_total", operation=operation)


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = AsyncQdrantClient(url=url, api_key=api_key, timeout=int(timeout))
        self._ensured: set[str] = set()
        # Cached because it cannot change under a running collection: a layout
        # is fixed at creation. Only ever an optimisation — every path that
        # reads it also handles a cold cache.
        self._layouts: dict[str, str] = {}

    async def _layout_of(self, name: str) -> str:
        """Whether this collection uses named vectors, cached per process.

        Collections created before Phase 4 hold one unnamed dense vector and no
        sparse vector at all. They are still queryable and must stay that way —
        the pre-knowledge-base corpus lives in one — so the store asks the
        collection what shape it is rather than assuming every collection is
        the shape this version creates.
        """
        cached = self._layouts.get(name)
        if cached is not None:
            return cached

        try:
            info = await self._client.get_collection(name)
            vectors = info.config.params.vectors
            layout = _NAMED if isinstance(vectors, dict) else _LEGACY
        except Exception:
            # A collection that does not exist yet will be created by this
            # version, so it will be named.
            layout = _NAMED

        self._layouts[name] = layout
        return layout

    async def ensure_collection(self, name: str, vector_size: int) -> None:
        """Create the collection and its payload indexes if they are missing.

        Safe to call from several workers at once, and safe to call on every
        ingestion. Two things make that true: an existing collection is never
        recreated — that would delete a live index to fix nothing — and a
        create that loses the race is caught rather than raised, because
        "someone else already made it" is the outcome we wanted.

        The in-process ``_ensured`` set only skips the round trip; correctness
        does not depend on it, which matters because each worker child has its
        own.
        """
        if name in self._ensured:
            return

        if not await self._client.collection_exists(name):
            try:
                await self._client.create_collection(
                    collection_name=name,
                    # Named from Phase 4 on, so a point can carry both halves of
                    # hybrid retrieval.
                    vectors_config={
                        DENSE_VECTOR: models.VectorParams(
                            size=vector_size, distance=models.Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        SPARSE_VECTOR: models.SparseVectorParams(
                            # The server computes inverse document frequency
                            # across the whole collection at query time. That is
                            # the part of a lexical score that needs to know what
                            # else is in the corpus, and having Qdrant do it is
                            # what removes the scroll-and-rebuild this replaced.
                            modifier=models.Modifier.IDF,
                        )
                    },
                )
                self._layouts[name] = _NAMED
                logger.info(
                    "created collection",
                    extra={"collection": name, "dim": vector_size, "sparse": True},
                )
            except Exception as exc:
                # Another worker got there first between the check and the
                # create. Only a genuine failure to exist afterwards is an error.
                if not await self._client.collection_exists(name):
                    raise VectorStoreUnavailable(
                        f"could not create collection {name}: {exc}", cause=exc
                    ) from exc
                logger.debug("collection created concurrently", extra={"collection": name})

        await self.ensure_indexes(name)
        self._ensured.add(name)

    async def ensure_indexes(self, name: str) -> None:
        """Create the payload indexes retrieval filters on.

        Idempotent: Qdrant rejects a duplicate index, and that rejection is the
        expected result on every call after the first.
        """
        wanted: list[tuple[str, models.PayloadSchemaType]] = [
            (field, models.PayloadSchemaType.KEYWORD) for field in KEYWORD_INDEXES
        ]
        wanted += [(field, models.PayloadSchemaType.BOOL) for field in BOOL_INDEXES]

        for field, schema in wanted:
            try:
                await self._client.create_payload_index(
                    collection_name=name, field_name=field, field_schema=schema
                )
            except Exception as exc:
                logger.debug("payload index present", extra={"field": field, "err": str(exc)})

    async def collection_dimension(self, name: str) -> int | None:
        """The vector width this collection was created with, or None if it does
        not exist. Read before indexing so a model change is caught before any
        points are written rather than as a per-point rejection."""
        try:
            info = await self._client.get_collection(name)
        except Exception:
            return None

        params = info.config.params.vectors
        # A named-vector collection reports a dict; a legacy one reports the
        # params directly. Both have to answer, because the dimension check
        # before indexing runs against whichever shape is actually there.
        if isinstance(params, dict):
            named = params.get(DENSE_VECTOR)
            size = getattr(named, "size", None)
        else:
            size = getattr(params, "size", None)
        return int(size) if size is not None else None

    async def upsert(
        self, collection: str, records: list[VectorRecord], batch_size: int = 128
    ) -> int:
        """Write points in batches, overwriting any that already exist.

        Upsert rather than insert is what makes a retry safe: point ids are
        derived from the version and chunk index, so a second pass over the same
        content lands on the same ids and replaces them instead of adding a
        parallel copy.
        """
        if not records:
            return 0

        named = await self._layout_of(collection) == _NAMED

        written = 0
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            points = [
                models.PointStruct(
                    id=record.id,
                    vector=self._vector_for(record, named),
                    payload={
                        TEXT_FIELD: record.text,
                        DOCUMENT_ID_FIELD: record.document_id,
                        **record.metadata,
                    },
                )
                for record in batch
            ]
            try:
                async with _observed("upsert"):
                    await self._client.upsert(collection_name=collection, points=points, wait=True)
            except Exception as exc:
                raise VectorStoreUnavailable(
                    f"upsert failed at point {start} of {len(records)}: {exc}", cause=exc
                ) from exc
            written += len(points)

        metrics.increment("vector_points_written_total", value=written)
        logger.info(
            events.VECTOR_UPSERT_COMPLETED,
            extra={
                "event": events.VECTOR_UPSERT_COMPLETED,
                "collection": collection,
                "points": written,
                "batches": (len(records) + batch_size - 1) // batch_size,
            },
        )
        return written

    @staticmethod
    def _vector_for(record: VectorRecord, named: bool) -> Any:
        """The point's vector payload, in whichever shape the collection uses."""
        if not named:
            return record.vector

        vectors: dict[str, Any] = {DENSE_VECTOR: record.vector}
        # An empty sparse vector is omitted rather than written as zero
        # coordinates: a chunk of pure punctuation has no lexical identity, and
        # a zero-length vector in the index is a row that can never match.
        if record.sparse is not None and not record.sparse.is_empty:
            vectors[SPARSE_VECTOR] = models.SparseVector(
                indices=record.sparse.indices, values=record.sparse.values
            )
        return vectors

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        named = await self._layout_of(collection) == _NAMED
        try:
            async with _observed("dense_search"):
                response = await self._client.query_points(
                    collection_name=collection,
                    query=vector,
                    using=DENSE_VECTOR if named else None,
                    limit=top_k,
                    query_filter=_to_filter(filters),
                    with_payload=True,
                )
        except Exception as exc:
            raise VectorStoreUnavailable(f"dense search failed: {exc}", cause=exc) from exc
        # The count, never the vectors and never the passages.
        metrics.observe("qdrant_result_count", len(response.points), operation="dense_search")
        return [_to_chunk(point, point.score) for point in response.points]

    async def search_sparse(
        self,
        collection: str,
        sparse: SparseVector,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Lexical search, scored inside Qdrant.

        Returns nothing for a query with no usable terms, and nothing for a
        collection that predates sparse vectors — in both cases there is no
        lexical ranking to be had, and an empty list degrades hybrid retrieval
        to dense-only rather than failing the request.
        """
        if sparse.is_empty:
            return []
        if await self._layout_of(collection) != _NAMED:
            logger.debug(
                "collection has no sparse vectors; lexical search skipped",
                extra={"collection": collection},
            )
            return []

        try:
            response = await self._client.query_points(
                collection_name=collection,
                query=models.SparseVector(indices=sparse.indices, values=sparse.values),
                using=SPARSE_VECTOR,
                limit=top_k,
                query_filter=_to_filter(filters),
                with_payload=True,
            )
        except Exception as exc:
            raise VectorStoreUnavailable(f"sparse search failed: {exc}", cause=exc) from exc
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
        return await self.delete_where(collection, {DOCUMENT_ID_FIELD: document_id})

    async def delete_where(
        self, collection: str, filters: dict[str, Any], exclude: dict[str, Any] | None = None
    ) -> int:
        """Delete every point matching ``filters`` but not ``exclude``.

        The empty-filter guard is the important line: ``_to_filter({})`` returns
        None, and a None selector deletes the whole collection. A caller whose
        filter dict came out empty by accident would take out every document in
        the knowledge base, so that case raises instead.
        """
        if not filters:
            raise ValueError("refusing to delete with an empty filter")
        selector = _to_filter(filters, exclude)
        if selector is None:
            raise ValueError("refusing to delete with an empty filter")

        try:
            if not await self._client.collection_exists(collection):
                # Nothing indexed yet, so nothing to remove. Deleting from a
                # collection that was never created is a no-op, not a failure.
                return 0
            before = await self._count_filtered(collection, selector)
            await self._client.delete(
                collection_name=collection,
                points_selector=models.FilterSelector(filter=selector),
                wait=True,
            )
        except Exception as exc:
            raise VectorStoreUnavailable(f"delete failed: {exc}", cause=exc) from exc
        return before

    async def set_flag(
        self, collection: str, filters: dict[str, Any], field: str, value: bool
    ) -> None:
        selector = _to_filter(filters)
        if selector is None:
            raise ValueError("refusing to set a payload flag with an empty filter")
        try:
            await self._client.set_payload(
                collection_name=collection,
                payload={field: value},
                points=selector,
                wait=True,
            )
        except Exception as exc:
            raise VectorStoreUnavailable(f"set_payload failed: {exc}", cause=exc) from exc

    async def count(self, collection: str) -> int:
        return await self._count_filtered(collection, None)

    async def count_where(self, collection: str, filters: dict[str, Any]) -> int:
        return await self._count_filtered(collection, _to_filter(filters))

    async def _count_filtered(self, collection: str, flt: models.Filter | None) -> int:
        result = await self._client.count(collection_name=collection, count_filter=flt, exact=True)
        return int(result.count)

    async def health(self) -> bool:  # noqa: D102 - see base class
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:
            logger.warning("qdrant health check failed", extra={"err": str(exc)})
            return False

    async def close(self) -> None:
        await self._client.close()
