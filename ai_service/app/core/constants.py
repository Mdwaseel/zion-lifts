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
CONFIDENCE_HIGH = 0.75
CONFIDENCE_LOW = 0.35

# --- Limits ------------------------------------------------------------------
MAX_QUESTION_CHARS = 4000
MAX_CONTEXT_CHARS = 12000
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_HISTORY_TURNS = 10


class SourceType(StrEnum):
    PDF = "pdf"
    WEB = "web"
    TEXT = "text"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
