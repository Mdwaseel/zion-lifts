"""What a worker process needs to run a task, built once per process.

Two costs make this worth caching rather than constructing per task. The
embedding model and the cross-encoder take tens of seconds to load and hundreds
of megabytes to hold, and the HTTP clients keep pooled connections that are only
useful if they outlive a single call.

The event loop is cached for the same reason. ``asyncio.run`` would create and
tear down a loop per task, and an ``httpx.AsyncClient`` is bound to the loop it
was created on — reusing one across loops is the kind of bug that shows up as an
occasional hang under load and never in a test.

Everything here is per *process*. Celery forks children, and each one builds its
own, which is exactly why worker concurrency is 1 by default.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.embeddings.factory import build_embeddings
from app.embeddings.provider import EmbeddingProvider
from app.ingestion.files import FileResolver, build_resolver
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.processors.chunker import RecursiveChunker
from app.ingestion.reporter import StageReporter
from app.retrieval.sparse import SparseEncoder
from app.vectorstore.base import VectorStore
from app.vectorstore.qdrant import QdrantVectorStore

logger = get_logger(__name__)

_loop: asyncio.AbstractEventLoop | None = None
_context: WorkerContext | None = None


@dataclass(slots=True)
class WorkerContext:
    settings: Settings
    embeddings: EmbeddingProvider
    store: VectorStore
    resolver: FileResolver
    reporter: StageReporter
    pipeline: IngestionPipeline

    async def aclose(self) -> None:
        await self.store.close()
        await self.resolver.close()
        await self.reporter.close()


def loop() -> asyncio.AbstractEventLoop:
    """This process's event loop, created on first use."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def run(coro: Any) -> Any:
    """Run one coroutine on the process loop."""
    return loop().run_until_complete(coro)


async def _build(settings: Settings) -> WorkerContext:
    embeddings = build_embeddings(settings)
    # Loaded here rather than on first use so a broken model configuration
    # fails when the worker starts, not on the first document a customer
    # uploads.
    await embeddings.load()

    store = QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=settings.qdrant_timeout,
    )
    resolver = build_resolver(settings)
    reporter = StageReporter(
        base_url=settings.backend_url or "",
        token=settings.ai_service_internal_token or "",
        timeout=settings.backend_timeout,
        retries=settings.backend_retries,
    )

    pipeline = IngestionPipeline(
        embeddings=embeddings,
        store=store,
        chunker=RecursiveChunker(settings.chunk_size, settings.chunk_overlap),
        resolver=resolver,
        reporter=reporter,
        embedding_model_version=settings.embedding_model_version,
        embed_batch_size=settings.embed_batch_size,
        upsert_batch_size=settings.vector_upsert_batch_size,
        sparse_encoder=SparseEncoder(max_terms=settings.sparse_max_terms),
    )

    logger.info(
        "worker runtime ready",
        extra={
            "embedding_model": embeddings.model_name,
            "dimension": embeddings.dimension,
            "storage": settings.document_storage,
        },
    )
    return WorkerContext(
        settings=settings,
        embeddings=embeddings,
        store=store,
        resolver=resolver,
        reporter=reporter,
        pipeline=pipeline,
    )


def context(settings: Settings | None = None) -> WorkerContext:
    """The cached runtime for this process."""
    global _context
    if _context is None:
        _context = run(_build(settings or get_settings()))
    return _context


def set_context(replacement: WorkerContext | None) -> None:
    """Install a runtime directly. For tests, which supply fakes rather than
    loading a real model and opening real sockets."""
    global _context
    _context = replacement


def shutdown() -> None:
    """Close the clients this process opened.

    Called from Celery's worker-shutdown signal so a restart does not leak
    sockets. Deliberately tolerant: a failure to close during shutdown must not
    turn a clean stop into a crash.
    """
    global _context, _loop
    if _context is not None:
        try:
            run(_context.aclose())
        except Exception as exc:  # pragma: no cover - shutdown path
            logger.warning("worker cleanup failed", extra={"err": str(exc)})
        _context = None
    if _loop is not None and not _loop.is_closed():
        _loop.close()
    _loop = None
