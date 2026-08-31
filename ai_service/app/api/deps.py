"""Composition root: builds the object graph once and hands it to routes.

Everything is constructed in `Container.build()` during app startup and reached
through `request.app.state.container`, so no module holds a global client and
tests can swap the container wholesale.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.embeddings.factory import build_embeddings
from app.embeddings.provider import EmbeddingProvider
from app.ingestion.processors.chunker import RecursiveChunker
from app.ingestion.service import IngestionService
from app.llm.fallback import FallbackLLM, build_llm
from app.rag.answer_generator import AnswerGenerator
from app.rag.context_builder import ContextBuilder
from app.rag.pipeline import RagPipeline
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.query_rewriter import QueryRewriter
from app.retrieval.reranker import (
    CrossEncoderReranker,
    NoopReranker,
    crossencoder_available,
)
from app.retrieval.scope import RetrievalScope
from app.retrieval.sparse import SparseEncoder
from app.retrieval.sparse_search import SparseSearch
from app.retrieval.vector_search import VectorSearch
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.vectorstore.base import VectorStore
from app.vectorstore.qdrant import QdrantVectorStore

logger = get_logger(__name__)


@dataclass(slots=True)
class Container:
    settings: Settings
    embeddings: EmbeddingProvider
    store: VectorStore
    llm: FallbackLLM
    ingestion: IngestionService
    pipeline: RagPipeline
    chat_service: ChatService
    document_service: DocumentService

    @classmethod
    async def build(cls, settings: Settings) -> Container:
        embeddings = build_embeddings(settings)
        await embeddings.load()

        store = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=settings.qdrant_timeout,
        )
        await store.ensure_collection(settings.qdrant_collection, embeddings.dimension)

        llm = build_llm(settings)

        ingestion = IngestionService(
            embeddings=embeddings,
            store=store,
            chunker=RecursiveChunker(settings.chunk_size, settings.chunk_overlap),
            default_collection=settings.qdrant_collection,
        )

        # Reranking is configured on but the model cannot be loaded in an image
        # built without sentence-transformers. Said once, here, because the
        # alternative is `rerank` catching the ImportError on every query and
        # returning fusion order with a line nobody reads.
        reranker: CrossEncoderReranker | NoopReranker
        if settings.reranker_enabled and not crossencoder_available():
            logger.error(
                "RERANKER_ENABLED is true but sentence-transformers is not installed; "
                "answering from fusion order instead. Install "
                "requirements-local-models.txt, or set RERANKER_ENABLED=false to "
                "make this deliberate",
                extra={"model": settings.reranker_model},
            )
            reranker = NoopReranker()
        elif settings.reranker_enabled:
            reranker = CrossEncoderReranker(settings.reranker_model, settings.embedding_device)
        else:
            reranker = NoopReranker()

        pipeline = RagPipeline(
            search=HybridSearch(
                vector_search=VectorSearch(embeddings, store),
                sparse_search=SparseSearch(
                    store, SparseEncoder(max_terms=settings.sparse_max_terms)
                ),
                alpha=settings.hybrid_alpha,
                dense_top_k=settings.dense_top_k,
                sparse_top_k=settings.sparse_top_k,
                fusion_top_k=settings.fusion_top_k,
                min_score=settings.min_retrieval_score,
                rrf_k=settings.rrf_k,
            ),
            reranker=reranker,
            generator=AnswerGenerator(
                llm=llm,
                context_builder=ContextBuilder(max_chars=settings.max_context_chars),
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            ),
            rewriter=QueryRewriter(llm, enabled=settings.query_rewrite_enabled),
            embedding_model=settings.embedding_model,
            embedding_model_version=settings.embedding_model_version,
            top_k=settings.rerank_top_k,
            min_rerank_score=settings.min_rerank_score,
            confidence_high=settings.confidence_high,
            confidence_low=settings.confidence_low,
            min_context_documents=settings.min_context_documents,
        )

        # Requests that name no knowledge base read the corpus indexed before
        # knowledge bases existed. Once documents are ingested through the
        # Django-owned models this becomes that deployment's default knowledge
        # base instead, and no caller has to change.
        default_scope = RetrievalScope.legacy(settings.qdrant_collection)

        logger.info("container ready", extra={"collection": settings.qdrant_collection})
        return cls(
            settings=settings,
            embeddings=embeddings,
            store=store,
            llm=llm,
            ingestion=ingestion,
            pipeline=pipeline,
            chat_service=ChatService(pipeline, default_scope=default_scope),
            document_service=DocumentService(ingestion),
        )

    async def close(self) -> None:
        await self.store.close()
        await self.llm.close()
        # Only the API embedding provider holds an HTTP client; the local one
        # and the router have nothing to release, so this is asked rather than
        # required of the interface.
        aclose = getattr(self.embeddings, "aclose", None)
        if callable(aclose):
            await aclose()


def get_container(request: Request) -> Container:
    container = getattr(request.app.state, "container", None)
    if container is None:  # pragma: no cover - startup guarantees this
        raise RuntimeError("Application container is not initialised.")
    return container


def get_chat_service(container: Container = Depends(get_container)) -> ChatService:
    return container.chat_service


def get_document_service(container: Container = Depends(get_container)) -> DocumentService:
    return container.document_service


def get_vector_store(container: Container = Depends(get_container)) -> VectorStore:
    return container.store


def get_llm(container: Container = Depends(get_container)) -> FallbackLLM:
    return container.llm


__all__ = [
    "Container",
    "Settings",
    "get_chat_service",
    "get_container",
    "get_document_service",
    "get_llm",
    "get_settings",
    "get_vector_store",
]
