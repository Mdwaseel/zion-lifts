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
from app.embeddings.huggingface import HuggingFaceEmbeddings
from app.embeddings.provider import EmbeddingProvider
from app.ingestion.processors.chunker import RecursiveChunker
from app.ingestion.service import IngestionService
from app.llm.fallback import FallbackLLM, build_llm
from app.rag.answer_generator import AnswerGenerator
from app.rag.context_builder import ContextBuilder
from app.rag.pipeline import RagPipeline
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.keyword_search import KeywordSearch
from app.retrieval.query_rewriter import QueryRewriter
from app.retrieval.reranker import CrossEncoderReranker, NoopReranker
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
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            device=settings.embedding_device,
            batch_size=settings.embedding_batch_size,
            cache_size=settings.embedding_cache_size,
        )
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

        reranker = (
            CrossEncoderReranker(settings.reranker_model, settings.embedding_device)
            if settings.reranker_enabled
            else NoopReranker()
        )

        pipeline = RagPipeline(
            search=HybridSearch(
                vector_search=VectorSearch(embeddings, store),
                keyword_search=KeywordSearch(store),
                alpha=settings.hybrid_alpha,
            ),
            reranker=reranker,
            generator=AnswerGenerator(
                llm=llm,
                context_builder=ContextBuilder(),
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            ),
            rewriter=QueryRewriter(llm, enabled=settings.query_rewrite_enabled),
            default_collection=settings.qdrant_collection,
            top_k=settings.top_k,
        )

        logger.info("container ready", extra={"collection": settings.qdrant_collection})
        return cls(
            settings=settings,
            embeddings=embeddings,
            store=store,
            llm=llm,
            ingestion=ingestion,
            pipeline=pipeline,
            chat_service=ChatService(pipeline),
            document_service=DocumentService(ingestion),
        )

    async def close(self) -> None:
        await self.store.close()
        await self.llm.close()


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
