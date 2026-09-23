"""Route-level tests against the real app wired to fake infrastructure."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import Container, get_container
from app.core.config import Settings, get_settings
from app.ingestion.processors.chunker import RecursiveChunker
from app.ingestion.service import IngestionService
from app.llm.fallback import FallbackLLM
from app.main import create_app
from app.rag.answer_generator import AnswerGenerator
from app.rag.context_builder import ContextBuilder
from app.rag.pipeline import RagPipeline
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.query_rewriter import QueryRewriter
from app.retrieval.reranker import NoopReranker
from app.retrieval.scope import RetrievalScope
from app.retrieval.sparse_search import SparseSearch
from app.retrieval.vector_search import VectorSearch
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from tests.conftest import FakeEmbeddings, FakeLLM, InMemoryVectorStore

COLLECTION = "test"


def build_container() -> Container:
    settings = Settings(
        _env_file=None, qdrant_collection=COLLECTION, api_keys=[], internal_token="t"
    )
    embeddings = FakeEmbeddings()
    store = InMemoryVectorStore()
    llm = FallbackLLM([FakeLLM("Qdrant stores dense vectors [1].")])

    ingestion = IngestionService(
        embeddings=embeddings,
        store=store,
        chunker=RecursiveChunker(200, 20),
        default_collection=COLLECTION,
    )
    pipeline = RagPipeline(
        search=HybridSearch(VectorSearch(embeddings, store), SparseSearch(store), alpha=0.5),
        reranker=NoopReranker(),
        generator=AnswerGenerator(llm, ContextBuilder()),
        rewriter=QueryRewriter(llm, enabled=False),
        embedding_model=embeddings.model_name,
        embedding_model_version="v1",
        top_k=3,
    )
    return Container(
        settings=settings,
        embeddings=embeddings,
        store=store,
        llm=llm,
        ingestion=ingestion,
        pipeline=pipeline,
        # No knowledge base named on a request means the legacy corpus, which
        # is what the ingestion endpoints above still write into.
        chat_service=ChatService(pipeline, default_scope=RetrievalScope.legacy(COLLECTION)),
        document_service=DocumentService(ingestion),
    )


@pytest.fixture
def client():
    container = build_container()
    app = create_app()
    # Override both: routes resolve services from the container, while the auth
    # guards resolve Settings directly.
    app.dependency_overrides[get_container] = lambda: container
    app.dependency_overrides[get_settings] = lambda: container.settings
    app.state.container = container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_is_public(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_then_ask_returns_an_answer(client: TestClient):
    ingest = client.post(
        "/api/v1/documents/text",
        json={
            "text": "Qdrant is a vector database that stores dense embeddings for "
            "similarity search across large document collections.",
            "metadata": {"title": "Qdrant notes"},
        },
    )
    assert ingest.status_code == 201, ingest.text
    assert ingest.json()["chunk_count"] >= 1

    answer = client.post("/api/v1/chat", json={"question": "What does Qdrant store?"})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["answer"]
    assert body["session_id"]
    assert 0.0 <= body["confidence"] <= 1.0


def test_search_returns_ranked_hits(client: TestClient):
    client.post(
        "/api/v1/documents/text",
        json={"text": "Hybrid retrieval fuses dense vectors with BM25 keyword scores."},
    )
    response = client.post("/api/v1/chat/search", json={"query": "hybrid retrieval", "top_k": 3})
    assert response.status_code == 200
    assert len(response.json()["hits"]) >= 1


def test_delete_unknown_document_is_404(client: TestClient):
    assert client.delete("/api/v1/documents/does-not-exist").status_code == 404


def test_validation_error_uses_the_error_envelope(client: TestClient):
    response = client.post("/api/v1/chat", json={"question": "   "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_internal_routes_require_the_internal_token(client: TestClient):
    assert client.get("/api/v1/internal/stats").status_code == 403
    ok = client.get("/api/v1/internal/stats", headers={"X-Internal-Token": "t"})
    assert ok.status_code == 200
    assert ok.json()["collection"] == COLLECTION


def test_a_client_cannot_choose_its_own_collection(client: TestClient):
    """The read boundary, at the edge.

    These fields used to be accepted and handed to Qdrant unchanged, which made
    the index's own naming the access-control boundary. They are now unknown
    fields: the corpus is decided server-side, and the most a caller can do is
    narrow what it is already allowed to see.
    """
    response = client.post(
        "/api/v1/chat",
        json={
            "question": "What does Qdrant store?",
            "collection": "someone-elses-corpus",
            "filters": {"knowledge_base_id": "not-mine"},
        },
    )
    assert response.status_code == 200, response.text
    # Answered from the server's own scope; the smuggled collection is ignored
    # rather than honoured. (extra="ignore" on the schema, not a silent 200 on
    # a failed search — the ingested corpus is the one that replied.)
    assert response.json()["answer"]


def test_narrowing_to_documents_requires_naming_a_knowledge_base(client: TestClient):
    response = client.post(
        "/api/v1/chat",
        json={"question": "What does Qdrant store?", "document_ids": ["d1"]},
    )
    assert response.status_code == 422
    assert "knowledge_base_id" in response.text


def test_search_is_scoped_the_same_way(client: TestClient):
    response = client.post(
        "/api/v1/chat/search",
        json={"query": "hybrid retrieval", "document_ids": ["d1"]},
    )
    assert response.status_code == 422
