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
from app.orchestration.assistant import AssistantPipeline
from app.orchestration.source_orchestrator import SourceOrchestrator
from app.query_router import QueryRouter
from app.query_router.classifier import LLMIntentClassifier, RuleIntentClassifier
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
from app.website.provider import WebsiteIndexProvider

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
    website: WebsiteIndexProvider | None = None
    assistant: AssistantPipeline | None = None

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
            # From the loaded provider, not from configuration: it is what
            # ingestion used to name the collection, and a settings value that
            # nobody sets would silently build a different name.
            embedding_dimension=embeddings.dimension,
            top_k=settings.rerank_top_k,
            min_rerank_score=settings.min_rerank_score,
            confidence_high=settings.confidence_high,
            confidence_low=settings.confidence_low,
            min_context_documents=settings.min_context_documents,
        )

        # Requests that name no knowledge base — every request the public
        # widget makes — read the deployment's default corpus.
        #
        # `DEFAULT_KNOWLEDGE_BASE_ID` is that corpus once documents are ingested
        # through the Django-owned models, which is the case the comment here
        # used to anticipate. Without it the default is the collection that
        # predates knowledge bases, and on a deployment that never used it that
        # collection is empty — so retrieval returns nothing and the assistant
        # refuses everything. No caller has to change either way.
        default_scope = (
            RetrievalScope.for_knowledge_base(knowledge_base_id=settings.default_knowledge_base_id)
            if settings.default_knowledge_base_id
            else RetrievalScope.legacy(settings.qdrant_collection)
        )

        # The routing layer. Built after the pipeline because it retrieves
        # *through* it: there is one retrieval path in this service, and the
        # orchestrator is a caller of it rather than a second one.
        website: WebsiteIndexProvider | None = None
        assistant: AssistantPipeline | None = None
        if settings.query_routing_enabled:
            website = WebsiteIndexProvider(
                base_url=settings.website_content_url,
                ttl_seconds=settings.website_index_ttl_seconds,
                timeout=settings.website_index_timeout,
            )
            # Failing here must not stop the service: the provider already holds
            # the static index, so the assistant comes up navigationally correct
            # and simply cannot name individual products until a refresh works.
            await website.start()

            classifier = (
                LLMIntentClassifier(llm, enabled=True)
                if settings.intent_llm_tiebreak
                else RuleIntentClassifier()
            )
            assistant = AssistantPipeline(
                router=QueryRouter(classifier, max_question_chars=None),
                orchestrator=SourceOrchestrator(
                    retriever=pipeline,
                    website=website,
                    context_size=settings.rerank_top_k,
                    diversity_lambda=settings.context_diversity_lambda,
                ),
                llm=llm,
                website=website,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                max_context_chars=settings.max_context_chars,
                confidence_high=settings.confidence_high,
                confidence_low=settings.confidence_low,
            )

        logger.info(
            "container ready",
            extra={
                "collection": settings.qdrant_collection,
                "routing": settings.query_routing_enabled,
                "website_pages": len(website.current) if website else 0,
            },
        )
        return cls(
            settings=settings,
            embeddings=embeddings,
            store=store,
            llm=llm,
            ingestion=ingestion,
            pipeline=pipeline,
            chat_service=ChatService(pipeline, default_scope=default_scope, assistant=assistant),
            document_service=DocumentService(ingestion),
            website=website,
            assistant=assistant,
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
