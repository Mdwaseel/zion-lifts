"""Orchestrates load -> clean -> chunk -> embed -> upsert."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.core.constants import SourceType
from app.core.logging import get_logger
from app.embeddings.provider import EmbeddingProvider
from app.ingestion.loaders.pdf_loader import PdfLoader
from app.ingestion.loaders.text_loader import LoadedDocument, TextLoader
from app.ingestion.loaders.web_loader import WebLoader
from app.ingestion.processors.chunker import RecursiveChunker
from app.ingestion.processors.cleaner import clean_text, strip_page_markers
from app.ingestion.processors.metadata import (
    build_payload,
    chunk_id,
    derive_title,
    new_document_id,
)
from app.vectorstore.base import VectorRecord, VectorStore

logger = get_logger(__name__)


@dataclass(slots=True)
class IngestionResult:
    document_id: str
    chunk_count: int
    collection: str
    title: str | None
    took_ms: float


class IngestionService:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        store: VectorStore,
        chunker: RecursiveChunker,
        default_collection: str,
        embed_batch_size: int = 64,
    ) -> None:
        self._embeddings = embeddings
        self._store = store
        self._chunker = chunker
        self._default_collection = default_collection
        self._batch_size = embed_batch_size
        self._text_loader = TextLoader()
        self._pdf_loader = PdfLoader()
        self._web_loader = WebLoader()

    # --- entry points --------------------------------------------------------

    async def ingest_text(
        self, text: str, metadata: dict[str, Any] | None = None, collection: str | None = None
    ) -> IngestionResult:
        source = (metadata or {}).get("source", "inline")
        document = self._text_loader.load_string(text, source=source)
        return await self._ingest(document, metadata, collection)

    async def ingest_pdf(
        self,
        data: bytes,
        filename: str,
        metadata: dict[str, Any] | None = None,
        collection: str | None = None,
    ) -> IngestionResult:
        document = await self._pdf_loader.load_bytes(data, filename)
        return await self._ingest(document, metadata, collection)

    async def ingest_file(
        self,
        data: bytes,
        filename: str,
        metadata: dict[str, Any] | None = None,
        collection: str | None = None,
    ) -> IngestionResult:
        if filename.lower().endswith(".pdf"):
            return await self.ingest_pdf(data, filename, metadata, collection)
        document = self._text_loader.load_bytes(data, filename)
        return await self._ingest(document, metadata, collection)

    async def ingest_url(
        self, url: str, metadata: dict[str, Any] | None = None, collection: str | None = None
    ) -> IngestionResult:
        document = await self._web_loader.load_url(url)
        return await self._ingest(document, metadata, collection)

    async def delete_document(self, document_id: str, collection: str | None = None) -> int:
        target = collection or self._default_collection
        removed = await self._store.delete_document(target, document_id)
        logger.info("document deleted", extra={"document_id": document_id, "chunks": removed})
        return removed

    # --- core pipeline -------------------------------------------------------

    async def _ingest(
        self,
        document: LoadedDocument,
        metadata: dict[str, Any] | None,
        collection: str | None,
    ) -> IngestionResult:
        started = time.perf_counter()
        target = collection or self._default_collection
        document_id = (metadata or {}).get("document_id") or new_document_id()

        cleaned = clean_text(document.text)
        if not cleaned:
            raise ValueError("Document contained no extractable text.")

        base_meta: dict[str, Any] = {
            "source": document.source,
            "source_type": SourceType(document.source_type).value,
            **{k: v for k, v in document.metadata.items() if v is not None},
            **{k: v for k, v in (metadata or {}).items() if v is not None},
        }
        base_meta.setdefault("title", derive_title(cleaned, document.source))
        base_meta.pop("document_id", None)

        chunks = self._chunker.split(cleaned, base_meta)
        if not chunks:
            raise ValueError("Chunking produced no chunks.")

        await self._store.ensure_collection(target, self._embeddings.dimension)

        total = 0
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start : start + self._batch_size]
            texts = [strip_page_markers(chunk.text) for chunk in batch]
            vectors = await self._embeddings.embed_documents(texts)
            records = [
                VectorRecord(
                    id=chunk_id(document_id, chunk.index),
                    vector=vector,
                    text=text,
                    document_id=document_id,
                    metadata=build_payload(chunk, document_id, base_meta, len(chunks)),
                )
                for chunk, text, vector in zip(batch, texts, vectors, strict=True)
            ]
            total += await self._store.upsert(target, records)

        took_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "document ingested",
            extra={"document_id": document_id, "chunks": total, "took_ms": round(took_ms, 1)},
        )
        return IngestionResult(
            document_id=document_id,
            chunk_count=total,
            collection=target,
            title=base_meta.get("title"),
            took_ms=took_ms,
        )
