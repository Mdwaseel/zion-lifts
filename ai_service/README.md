# AI Service

A production-shaped RAG (retrieval-augmented generation) API built with FastAPI.
Ingest PDFs, web pages and raw text; ask questions and get answers with inline
citations, a confidence score, and automatic failover across LLM providers.

## How it works

```
ingest    load -> clean -> chunk -> embed -> upsert (Qdrant)
query     rewrite -> hybrid search (dense + BM25, fused by RRF)
                  -> cross-encoder rerank -> confidence gate
                  -> generate with citations (Gemini -> Groq -> OpenAI)
```

Each stage sits behind an interface, so any piece can be swapped without
touching the rest: `VectorStore`, `EmbeddingProvider` and `LLMClient` are all
abstract base classes with concrete implementations wired up in one place.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate on Unix
pip install -r requirements.txt

cp .env.example .env            # add at least one LLM API key
docker run -p 6333:6333 -v "$PWD/qdrant_storage:/qdrant/storage" qdrant/qdrant

uvicorn app.main:app --reload
```

Open http://localhost:8000/docs.

Or run the whole stack:

```bash
cd docker && docker compose up --build
```

## Using the API

Ingest a document:

```bash
curl -X POST localhost:8000/api/v1/documents/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Qdrant stores dense vectors.", "metadata": {"title": "Notes"}}'
```

Upload a PDF:

```bash
curl -X POST localhost:8000/api/v1/documents/upload \
  -F "file=@handbook.pdf" \
  -F 'metadata={"title": "Handbook", "tags": ["hr"]}'
```

Ask a question:

```bash
curl -X POST localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What does Qdrant store?"}'
```

```json
{
  "answer": "Qdrant stores dense vector embeddings [1].",
  "citations": [{"marker": "[1]", "document_id": "…", "title": "Notes", "snippet": "…"}],
  "confidence": 0.81,
  "confidence_level": "high",
  "provider": "gemini"
}
```

Stream it with `POST /api/v1/chat/stream` (server-sent events), or inspect
retrieval alone with `POST /api/v1/chat/search`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/health` | Liveness. Touches nothing downstream. |
| GET | `/api/v1/ready` | Readiness. Checks Qdrant and the LLM chain. |
| POST | `/api/v1/chat` | Ask a grounded question. |
| POST | `/api/v1/chat/stream` | Same, streamed as SSE. |
| POST | `/api/v1/chat/search` | Retrieval only, no generation. |
| POST | `/api/v1/documents/text` | Ingest raw text. |
| POST | `/api/v1/documents/url` | Fetch and ingest a web page. |
| POST | `/api/v1/documents/upload` | Upload a PDF or text file. |
| DELETE | `/api/v1/documents/{id}` | Delete a document and its chunks. |
| GET | `/api/v1/internal/stats` | Index, cache and circuit-breaker state. |

Public routes take `X-API-Key` when `API_KEYS` is set (auth is skipped when it is
empty, for local development). Internal routes always require `X-Internal-Token`.

## Design notes

**Hybrid retrieval.** Dense search misses exact identifiers and rare proper
nouns; BM25 catches those. Reciprocal rank fusion combines the two by rank, so
cosine similarity and BM25 scores never have to be calibrated against each other.
Tune the balance with `HYBRID_ALPHA` (1.0 = pure vector, 0.0 = pure keyword).

**Confidence gating.** `app/retrieval/confidence.py` blends top relevance, mean
support and agreement across distinct documents. Below the low threshold the
pipeline refuses instead of generating a fluent answer from weak evidence.

**Citations are verified, not trusted.** The model is asked to cite `[n]` markers;
`app/rag/citation_handler.py` strips any marker pointing past the end of the
context, so a hallucinated `[7]` never ships as a resolvable source.

**Provider failover.** `FallbackLLM` walks the configured provider order, each
guarded by its own circuit breaker. A provider that fails repeatedly is skipped
entirely until its reset window elapses. Streaming only fails over before the
first token — once output has reached the client, splicing in a second model's
answer would corrupt it.

**Blocking work stays off the event loop.** Embedding and reranking are CPU-bound
and run in worker threads via `asyncio.to_thread`.

## Configuration

Everything is environment-driven through `app/core/config.py`; see `.env.example`
for the full list. The knobs you are most likely to touch:

| Variable | Default | Notes |
| --- | --- | --- |
| `LLM_PROVIDER_ORDER` | `gemini,groq,openai` | Failover order. Unconfigured providers are skipped. |
| `TOP_K` | `5` | Passages passed to the model. |
| `HYBRID_ALPHA` | `0.5` | Dense/keyword balance. |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `120` | Characters. |
| `RERANKER_ENABLED` | `true` | Disable to cut ~200 MB of weights and latency. |
| `API_KEYS` | *(empty)* | Comma-separated. Empty disables public auth. |

## Development

```bash
pip install -r requirements-dev.txt

pytest                    # unit + integration, no external services needed
pytest -m evaluation      # quality benchmarks
ruff check . && mypy app
```

Unit and integration tests run entirely against in-memory fakes
(`tests/conftest.py`): a hash-based embedder, an in-memory vector store and a
scripted LLM. No Qdrant, no API keys, no model downloads.

## Scripts

```bash
python -m scripts.ingest ./docs --collection handbook --tag hr
python -m scripts.evaluate tests/evaluation/dataset.jsonl --top-k 5 --out report.json
```

`evaluate.py` reports hit@k, MRR, precision@k, mean confidence and p50 latency
against a labelled JSONL question set.

## Layout

```
app/
  api/         routes, schemas, and the dependency container
  core/        config, logging, security, constants
  ingestion/   loaders (pdf/web/text), processors (clean/chunk/metadata)
  embeddings/  provider interface, HuggingFace impl, LRU cache
  retrieval/   vector, keyword, hybrid, reranker, rewriter, confidence
  vectorstore/ VectorStore interface, Qdrant impl, collection specs
  llm/         LLMClient interface, providers, fallback, circuit breaker
  rag/         pipeline, context builder, answer generator, citations
  prompts/     system, RAG and rewrite templates
  services/    chat and document application services
```
