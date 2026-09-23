"""The event vocabulary, as constants rather than strings at each call site.

Every structured log line carries an ``event`` field drawn from this module.
The point is not tidiness — it is that an operator can grep for one name and
find every occurrence, and that renaming an event is a change to one line here
instead of a search that misses the two spellings nobody remembered.

The list is deliberately short. An event marks something an operator would act
on: a stage boundary, a fallback, a refusal, a dependency failing. Logging every
function entry would produce a vocabulary too large to learn and too noisy to
alert on, so intermediate detail belongs in the *fields* of these events rather
than in events of its own.

Naming is ``subject_verb`` in the past tense, because these describe things that
have happened. ``_started`` events exist only where the gap between start and
finish is itself diagnostic — a stage that never completes is found by the
absence of its completion, and that only works if the start was recorded.
"""

from __future__ import annotations

from typing import Final

# --- HTTP requests -----------------------------------------------------------
REQUEST_STARTED: Final = "request_started"
REQUEST_COMPLETED: Final = "request_completed"
REQUEST_FAILED: Final = "request_failed"

# --- ingestion ---------------------------------------------------------------
INGESTION_QUEUED: Final = "ingestion_queued"
INGESTION_STARTED: Final = "ingestion_started"
INGESTION_STAGE_STARTED: Final = "ingestion_stage_started"
INGESTION_STAGE_COMPLETED: Final = "ingestion_stage_completed"
INGESTION_COMPLETED: Final = "ingestion_completed"
INGESTION_FAILED: Final = "ingestion_failed"
INGESTION_RETRYING: Final = "ingestion_retrying"

# --- embeddings --------------------------------------------------------------
EMBEDDING_STARTED: Final = "embedding_started"
EMBEDDING_COMPLETED: Final = "embedding_completed"
EMBEDDING_FALLBACK: Final = "embedding_fallback"
EMBEDDING_RECOVERED: Final = "embedding_recovered"
EMBEDDING_FAILED: Final = "embedding_failed"

# --- vector store ------------------------------------------------------------
VECTOR_UPSERT_STARTED: Final = "vector_upsert_started"
VECTOR_UPSERT_COMPLETED: Final = "vector_upsert_completed"
VECTOR_UPSERT_FAILED: Final = "vector_upsert_failed"
VECTOR_SEARCH_COMPLETED: Final = "vector_search_completed"
VECTOR_SEARCH_FAILED: Final = "vector_search_failed"

# --- retrieval ---------------------------------------------------------------
RETRIEVAL_STARTED: Final = "retrieval_started"
DENSE_RETRIEVAL_COMPLETED: Final = "dense_retrieval_completed"
SPARSE_RETRIEVAL_COMPLETED: Final = "sparse_retrieval_completed"
HYBRID_RETRIEVAL_COMPLETED: Final = "hybrid_retrieval_completed"
RERANKING_COMPLETED: Final = "reranking_completed"
RETRIEVAL_FAILED: Final = "retrieval_failed"

# --- grounding ---------------------------------------------------------------
GROUNDING_PASSED: Final = "grounding_passed"
GROUNDING_REFUSED: Final = "grounding_refused"

# --- generation --------------------------------------------------------------
LLM_STARTED: Final = "llm_started"
LLM_COMPLETED: Final = "llm_completed"
LLM_FALLBACK: Final = "llm_fallback"
LLM_FAILED: Final = "llm_failed"
CITATION_GENERATED: Final = "citation_generated"
CITATION_VALIDATION_FAILED: Final = "citation_validation_failed"

# --- chat --------------------------------------------------------------------
CHAT_STARTED: Final = "chat_started"
CHAT_COMPLETED: Final = "chat_completed"
CHAT_FAILED: Final = "chat_failed"

# --- streaming ---------------------------------------------------------------
# A stream that opened is not a stream that worked. These four are what
# distinguish "answered", "died mid-answer" and "the reader walked away", which
# an HTTP status code alone cannot: the status is 200 before a single token is
# produced.
STREAM_STARTED: Final = "stream_started"
STREAM_FIRST_TOKEN: Final = "stream_first_token"
STREAM_COMPLETED: Final = "stream_completed"
STREAM_FAILED: Final = "stream_failed"
STREAM_CANCELLED: Final = "stream_cancelled"

# --- celery ------------------------------------------------------------------
CELERY_TASK_STARTED: Final = "celery_task_started"
CELERY_TASK_COMPLETED: Final = "celery_task_completed"
CELERY_TASK_FAILED: Final = "celery_task_failed"
CELERY_TASK_RETRYING: Final = "celery_task_retrying"

# --- providers and dependencies ----------------------------------------------
CIRCUIT_OPENED: Final = "circuit_opened"
CIRCUIT_HALF_OPEN: Final = "circuit_half_open"
CIRCUIT_CLOSED: Final = "circuit_closed"
DEPENDENCY_UNAVAILABLE: Final = "dependency_unavailable"
