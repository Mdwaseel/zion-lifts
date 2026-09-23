"""Version-aware ingestion: one document version, from stored bytes to searchable.

The Celery task is a wrapper. This is the workflow, and it is written to hold
four properties that matter more than throughput.

**A partial index is never searchable.** Chunks are written with
``active=False`` and flipped in a single server-side call once the whole version
has been written. A run that dies at chunk 700 of 1000 leaves 700 chunks that
nothing will retrieve, rather than 700 chunks answering questions as though they
were a complete document.

**The live edition keeps answering.** Nothing belonging to the previous version
is touched until the new one is fully written. Version 2 failing leaves version
1 exactly as it was — same points, same flag, same answers.

**A retry costs work, never correctness.** Point ids are derived from the
version and the chunk index, so a second pass writes to the same ids and
replaces them. Re-embedding on retry is deliberate: it is a few seconds of CPU
in exchange for not having to keep intermediate state consistent across process
restarts.

**The backend hears about every stage.** Each step reports before it starts, so
a document stuck in EMBEDDING names the dependency to go and look at.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.api.schemas.document import IngestionReport, IngestionRequest
from app.core import events
from app.core.constants import DocumentStatus, SourceType
from app.core.errors import (
    EmbeddingDimensionMismatch,
    EmbeddingFailed,
    IngestionError,
    InvalidDocument,
    PdfExtractionFailed,
    classify,
)
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.embeddings.provider import EmbeddingProvider
from app.ingestion.files import FileResolver
from app.ingestion.loaders.pdf_loader import PdfLoader
from app.ingestion.processors.chunker import RecursiveChunker
from app.ingestion.processors.cleaner import assign_pages, clean_text, strip_page_markers
from app.ingestion.processors.metadata import content_hash
from app.ingestion.reporter import StageReporter
from app.retrieval.sparse import SparseEncoder
from app.vectorstore.base import SparseVector, VectorRecord, VectorStore
from app.vectorstore.collections import (
    ACTIVE_FIELD,
    DOCUMENT_VERSION_ID_FIELD,
    KNOWLEDGE_BASE_ID_FIELD,
    CollectionNameBuilder,
)

logger = get_logger(__name__)

# Namespace for deterministic point ids. Fixed for the life of the index: change
# it and every existing point becomes an orphan nothing will ever overwrite.
_POINT_NAMESPACE = uuid.UUID("6f0d3c58-8a2f-4c1b-9d77-2a5f4b1e9c30")


def point_id(document_version_id: str, chunk_index: int) -> str:
    """The id chunk *n* of a version always gets.

    Derived from the version and the position, and nothing else. Including the
    chunk's content hash would be more precise and much worse: re-chunking the
    same version would then write a fresh set of ids beside the old ones, and
    the old ones would stay in the index for ever with no way to find them.
    """
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{document_version_id}/{chunk_index}"))


@dataclass(slots=True)
class IngestionOutcome:
    document_version_id: str
    collection: str
    page_count: int
    chunk_count: int
    embedding_model: str
    embedding_dimension: int
    took_ms: float
    stage_timings: dict[str, float] = field(default_factory=dict)


class IngestionPipeline:
    """Runs one operation against one document version."""

    def __init__(
        self,
        *,
        embeddings: EmbeddingProvider,
        store: VectorStore,
        chunker: RecursiveChunker,
        resolver: FileResolver,
        reporter: StageReporter,
        embedding_model_version: str,
        embed_batch_size: int = 64,
        upsert_batch_size: int = 128,
        sparse_encoder: SparseEncoder | None = None,
    ) -> None:
        self._embeddings = embeddings
        self._store = store
        self._chunker = chunker
        self._resolver = resolver
        self._reporter = reporter
        self._embedding_model_version = embedding_model_version
        self._embed_batch_size = embed_batch_size
        self._upsert_batch_size = upsert_batch_size
        # Cheap, deterministic and corpus-independent: the lexical half of a
        # chunk is computed here, at ingestion, and Qdrant applies IDF across
        # the collection at query time.
        self._sparse = sparse_encoder or SparseEncoder()
        self._pdf = PdfLoader()

    # --- reporting -----------------------------------------------------------

    async def _report(
        self, request: IngestionRequest, stage: DocumentStatus, progress: int, **extra: Any
    ) -> None:
        report = IngestionReport(
            job_id=request.job_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            stage=stage,
            progress=progress,
            **extra,
        )
        await self._reporter.send(report.model_dump(exclude_none=True, mode="json"))

    def _log_context(self, request: IngestionRequest) -> dict[str, Any]:
        """Identifiers only. Never a filename's contents, never a passage."""
        return {
            "job_id": request.job_id,
            "document_id": request.document_id,
            "document_version_id": request.document_version_id,
            "knowledge_base_id": request.knowledge_base_id,
            "operation": str(request.operation),
        }

    def collection_for(self, request: IngestionRequest, dimension: int | None = None) -> str:
        """Where this version's vectors belong.

        The embedding model is taken from the *provider actually in use*, not
        from the request. If a fallback provider answered, its identity is what
        names the collection — writing its vectors into the primary model's
        collection would put two incompatible geometries in one index.
        """
        return CollectionNameBuilder.build(
            knowledge_base_id=request.knowledge_base_id,
            embedding_model=self._embeddings.model_name,
            embedding_model_version=self._embedding_model_version,
            embedding_dimension=dimension or self._embeddings.dimension,
        )

    # --- the workflow --------------------------------------------------------

    async def ingest(self, request: IngestionRequest) -> IngestionOutcome:
        started = time.perf_counter()
        context = self._log_context(request)
        timings: dict[str, float] = {}
        metrics.increment("ingestion_jobs_total", operation=str(request.operation))
        logger.info(events.INGESTION_STARTED, extra={"event": events.INGESTION_STARTED, **context})

        await self._report(request, DocumentStatus.PROCESSING, 0)

        # --- resolve ---------------------------------------------------------
        mark = time.perf_counter()
        if not request.file_reference:
            raise InvalidDocument("the request carries no file reference")
        data = await self._resolver.fetch_verified(request.file_reference, request.content_hash)
        if not data:
            raise InvalidDocument("the stored file is empty")
        timings["resolve"] = (time.perf_counter() - mark) * 1000
        metrics.observe("ingestion_stage_duration", timings["resolve"], stage="resolve")

        # --- extract ---------------------------------------------------------
        await self._report(request, DocumentStatus.EXTRACTING, 20)
        mark = time.perf_counter()
        try:
            loaded = await self._pdf.load_bytes(data, request.file_reference)
        except IngestionError:
            raise
        except Exception as exc:
            raise PdfExtractionFailed(f"could not read the PDF: {exc}", cause=exc) from exc

        cleaned = clean_text(loaded.text)
        if not cleaned.strip():
            # A scanned PDF with no text layer reaches here. Permanent: the same
            # bytes will produce the same nothing on every retry, and the fix is
            # OCR or a different file, not another attempt.
            raise InvalidDocument("no extractable text — the PDF may be a scan with no text layer")
        page_count = int(loaded.metadata.get("pages") or 0)
        timings["extract"] = (time.perf_counter() - mark) * 1000
        metrics.observe("ingestion_stage_duration", timings["extract"], stage="extract")
        metrics.observe("extraction_duration", timings["extract"])
        logger.info(
            events.INGESTION_STAGE_COMPLETED,
            extra={
                **context,
                "stage": "extract",
                "pages": page_count,
                "duration_ms": round(timings["extract"], 1),
            },
        )

        # --- chunk -----------------------------------------------------------
        await self._report(request, DocumentStatus.CHUNKING, 40, page_count=page_count)
        mark = time.perf_counter()
        chunks = self._chunker.split(cleaned, {})
        if not chunks:
            raise InvalidDocument("chunking produced nothing to index")
        timings["chunk"] = (time.perf_counter() - mark) * 1000
        metrics.observe("ingestion_stage_duration", timings["chunk"], stage="chunk")
        metrics.observe("chunking_duration", timings["chunk"])
        logger.info(
            events.INGESTION_STAGE_COMPLETED,
            extra={
                **context,
                "stage": "chunk",
                "chunks": len(chunks),
                "duration_ms": round(timings["chunk"], 1),
            },
        )

        # --- embed -----------------------------------------------------------
        await self._report(
            request,
            DocumentStatus.EMBEDDING,
            60,
            page_count=page_count,
            chunk_count=len(chunks),
        )
        mark = time.perf_counter()
        texts = [strip_page_markers(chunk.text) for chunk in chunks]
        vectors = await self._embed(texts)
        timings["embed"] = (time.perf_counter() - mark) * 1000
        metrics.observe("ingestion_stage_duration", timings["embed"], stage="embed")
        metrics.observe("embedding_duration", timings["embed"], source="ingestion")
        logger.info(
            events.INGESTION_STAGE_COMPLETED,
            extra={
                **context,
                "stage": "embed",
                "chunks": len(vectors),
                "duration_ms": round(timings["embed"], 1),
            },
        )

        # --- index -----------------------------------------------------------
        # Named *after* embedding, not before: if the fallback model answered,
        # the collection has to be its own. See app/embeddings/router.py.
        collection = self.collection_for(request, dimension=len(vectors[0]) if vectors else None)
        await self._report(
            request,
            DocumentStatus.INDEXING,
            80,
            page_count=page_count,
            chunk_count=len(chunks),
            collection=collection,
        )
        mark = time.perf_counter()
        dimension = await self._index(request, collection, chunks, texts, vectors, page_count)
        timings["index"] = (time.perf_counter() - mark) * 1000
        metrics.observe("ingestion_stage_duration", timings["index"], stage="index")
        metrics.observe("indexing_duration", timings["index"])
        logger.info(
            events.INGESTION_STAGE_COMPLETED,
            extra={
                **context,
                "stage": "index",
                "chunks": len(vectors),
                "collection": collection,
                "duration_ms": round(timings["index"], 1),
            },
        )

        took_ms = (time.perf_counter() - started) * 1000

        # READY is reported last, after the flag flip. Until this message the
        # backend has no reason to make the version active, and it is the
        # backend that decides whether it does.
        await self._report(
            request,
            DocumentStatus.READY,
            100,
            page_count=page_count,
            chunk_count=len(chunks),
            collection=collection,
            embedding_model=self._embeddings.model_name,
            embedding_model_version=self._embedding_model_version,
            embedding_dimension=dimension,
        )
        metrics.increment("ingestion_jobs_success_total", operation=str(request.operation))
        metrics.observe("ingestion_duration", took_ms, operation=str(request.operation))
        metrics.increment("ingestion_chunks_total", value=len(chunks))
        metrics.increment("ingestion_pages_total", value=page_count)
        logger.info(
            events.INGESTION_COMPLETED,
            extra={
                "event": events.INGESTION_COMPLETED,
                **context,
                "chunk_count": len(chunks),
                "page_count": page_count,
                "embedding_batch_count": (len(chunks) + self._embed_batch_size - 1)
                // self._embed_batch_size,
                "vector_count": len(chunks),
                "collection": collection,
                "duration_ms": round(took_ms, 1),
                **{f"{stage}_ms": round(value, 1) for stage, value in timings.items()},
            },
        )

        return IngestionOutcome(
            document_version_id=request.document_version_id,
            collection=collection,
            page_count=page_count,
            chunk_count=len(chunks),
            embedding_model=self._embeddings.model_name,
            embedding_dimension=dimension,
            took_ms=took_ms,
            stage_timings=timings,
        )

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._embed_batch_size):
            batch = texts[start : start + self._embed_batch_size]
            try:
                vectors.extend(await self._embeddings.embed_documents(batch))
            except Exception as exc:
                # Retryable: a provider timing out or rate-limiting is the
                # common case, and the same call usually succeeds later.
                raise EmbeddingFailed(
                    f"embedding failed at text {start} of {len(texts)}: {exc}", cause=exc
                ) from exc

        if len(vectors) != len(texts):
            raise EmbeddingFailed(
                f"embedding returned {len(vectors)} vectors for {len(texts)} chunks"
            )
        return vectors

    async def _index(
        self,
        request: IngestionRequest,
        collection: str,
        chunks: list[Any],
        texts: list[str],
        vectors: list[list[float]],
        page_count: int,
    ) -> int:
        dimension = len(vectors[0]) if vectors else self._embeddings.dimension

        await self._store.ensure_collection(collection, dimension)

        # Checked against the collection as it actually exists, before a single
        # point is written. A model swap that changed the vector width would
        # otherwise be discovered one rejected upsert at a time, halfway
        # through, with the first half already stored.
        existing = getattr(self._store, "collection_dimension", None)
        if existing is not None:
            actual = await self._store.collection_dimension(collection)  # type: ignore[attr-defined]
            if actual is not None and actual != dimension:
                raise EmbeddingDimensionMismatch(
                    f"{collection} stores {actual}-dimensional vectors but "
                    f"{self._embeddings.model_name} produced {dimension}. The collection "
                    "name must change with the embedding — bump EMBEDDING_MODEL_VERSION."
                )

        # Page numbers are resolved across the whole ordered set rather than
        # per chunk — see cleaner.assign_pages for why a chunk in isolation
        # usually has no page at all.
        pages = assign_pages([chunk.text for chunk in chunks])

        records = [
            VectorRecord(
                id=point_id(request.document_version_id, chunk.index),
                vector=vector,
                sparse=self._sparse_for(text),
                text=text,
                document_id=request.document_id,
                metadata={
                    KNOWLEDGE_BASE_ID_FIELD: request.knowledge_base_id,
                    DOCUMENT_VERSION_ID_FIELD: request.document_version_id,
                    "chunk_index": chunk.index,
                    "chunk_id": point_id(request.document_version_id, chunk.index),
                    "page": page,
                    "source": request.file_reference.rsplit("/", 1)[-1],
                    "source_type": str(SourceType.PDF),
                    "content_hash": content_hash(text),
                    "document_content_hash": request.content_hash,
                    "total_chunks": len(chunks),
                    # Written invisible. Flipped once, below, when the whole
                    # version is on disk.
                    ACTIVE_FIELD: False,
                },
            )
            for chunk, text, vector, page in zip(chunks, texts, vectors, pages, strict=True)
        ]

        written = await self._store.upsert(collection, records, batch_size=self._upsert_batch_size)
        if written != len(records):
            raise IngestionError(f"wrote {written} of {len(records)} chunks")

        await self._activate(request, collection, len(records))
        return dimension

    def _sparse_for(self, text: str) -> SparseVector:
        encoded = self._sparse.encode(text)
        return SparseVector(indices=encoded.indices, values=encoded.values)

    async def _activate(self, request: IngestionRequest, collection: str, chunk_count: int) -> None:
        """Make this version searchable and retire the one it replaces.

        Two server-side calls, and their order is the whole safety property:

        1. flip this version's chunks to active — it becomes answerable;
        2. delete every other edition of the same document.

        New first, old second, deliberately. For the few milliseconds between
        the two calls both editions are searchable, which is a superset of the
        right answer; reversing the order would instead leave a window in which
        the document is in *neither* edition and simply vanishes from search.
        An overlap degrades an answer, a gap loses it.

        Step 2 failing is survivable: the new edition is already answering, and
        the leftovers are dead weight the next run clears.
        """
        version_filter = {
            KNOWLEDGE_BASE_ID_FIELD: request.knowledge_base_id,
            DOCUMENT_VERSION_ID_FIELD: request.document_version_id,
        }
        await self._store.set_flag(collection, version_filter, ACTIVE_FIELD, True)

        indexed = await self._store.count_where(collection, version_filter)
        if indexed < chunk_count:
            raise IngestionError(
                f"only {indexed} of {chunk_count} chunks are in {collection} after indexing"
            )

        await self._retire_previous(request, collection)

    async def _retire_previous(self, request: IngestionRequest, collection: str) -> None:
        """Remove the editions this one supersedes.

        Best effort on purpose. The new version is already active and already
        answering; a failure to tidy up the old one is an index that is larger
        than it needs to be, not an index that is wrong. Raising here would fail
        a run that had actually succeeded.
        """
        try:
            removed = await self._store.delete_where(
                collection,
                {
                    KNOWLEDGE_BASE_ID_FIELD: request.knowledge_base_id,
                    "document_id": request.document_id,
                },
                # Everything for this document *except* the edition that just
                # landed. Matching on active=False instead would miss the
                # previous edition, whose chunks are active — which is exactly
                # the point of retiring them.
                exclude={DOCUMENT_VERSION_ID_FIELD: request.document_version_id},
            )
            if removed:
                logger.info(
                    "retired superseded chunks",
                    extra={**self._log_context(request), "removed": removed},
                )
        except Exception as exc:
            logger.warning(
                "could not retire superseded chunks",
                extra={**self._log_context(request), "err": str(exc)},
            )

    # --- other operations ----------------------------------------------------

    async def reindex(self, request: IngestionRequest) -> IngestionOutcome:
        """Rebuild one version's vectors in place.

        The same work as ``ingest`` against the same version id, which is what
        keeps it safe: the same point ids are written, so the rebuild replaces
        its own chunks rather than adding a second copy, and the previous
        edition stays active until the rebuild has finished.
        """
        return await self.ingest(request)

    async def delete(self, request: IngestionRequest) -> int:
        """Remove one document's chunks from the index.

        Scoped by knowledge base and document, never by collection: dropping a
        collection to delete one document would take every other document in
        that knowledge base with it.

        Idempotent. Deleting something already deleted removes nothing and
        reports success — a redelivered message must not turn a completed
        deletion into a failed job.
        """
        context = self._log_context(request)
        collection = self.collection_for(request)

        # Every edition of this document, in this knowledge base. Deletion is a
        # whole-document operation: individual versions are retired by
        # `_activate` when their successor lands, never by a delete message.
        filters: dict[str, Any] = {
            KNOWLEDGE_BASE_ID_FIELD: request.knowledge_base_id,
            "document_id": request.document_id,
        }

        await self._report(request, DocumentStatus.DELETING, 50)
        try:
            removed = await self._store.delete_where(collection, filters)
        except Exception as exc:
            raise classify(exc) from exc

        await self._report(request, DocumentStatus.DELETED, 100, chunk_count=0)
        logger.info("document deleted from index", extra={**context, "removed": removed})
        return removed

    async def report_failure(self, request: IngestionRequest, error: IngestionError) -> None:
        """Tell the backend a run has ended badly.

        Sent only when the task has given up — a retryable error that is about
        to be retried leaves the job RUNNING, because it is.
        """
        await self._report(
            request,
            DocumentStatus.FAILED,
            0,
            **error.as_report(),
        )
