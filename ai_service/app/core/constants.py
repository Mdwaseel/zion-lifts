"""Project-wide constants. No imports from other app modules allowed here."""

from enum import StrEnum

SERVICE_NAME = "ai_service"

# --- Collections -------------------------------------------------------------
DEFAULT_COLLECTION = "documents"

# --- Chunking ----------------------------------------------------------------
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120
MIN_CHUNK_CHARS = 50

# --- Retrieval ---------------------------------------------------------------
DEFAULT_TOP_K = 5
CANDIDATE_MULTIPLIER = 4  # fetch top_k * N candidates before reranking
RRF_K = 60  # reciprocal rank fusion smoothing constant

# --- Confidence bands --------------------------------------------------------
# Defaults only. The live values are Settings.confidence_high / confidence_low,
# so an operator can tune the refusal threshold without a deploy.
CONFIDENCE_HIGH = 0.75
CONFIDENCE_LOW = 0.35

# Rough English average across the tokenizers in use. Only ever used to turn a
# token budget into the character budget the context builder measures in, so a
# small error costs a little unused window rather than a truncated prompt.
CHARS_PER_TOKEN = 4

# --- Limits ------------------------------------------------------------------
MAX_QUESTION_CHARS = 4000
MAX_CONTEXT_CHARS = 12000
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_HISTORY_TURNS = 10


class SourceType(StrEnum):
    PDF = "pdf"
    WEB = "web"
    TEXT = "text"


class JobOperation(StrEnum):
    """What a worker has been asked to do. Mirrors JobType on the Django side;
    the two are a shared vocabulary that no import enforces, so they change
    together."""

    INGEST = "ingest"
    REINDEX = "reindex"
    DELETE = "delete"


class DocumentStatus(StrEnum):
    """The stages the worker reports.

    Deliberately identical to ``DocumentState`` in the Django app: the two are
    one vocabulary spoken across a service boundary, and a value here that the
    backend does not recognise is a report it will reject.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
