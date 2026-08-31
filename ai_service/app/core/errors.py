"""Ingestion failures, as codes an operator can act on.

Two decisions live here, and both matter more than the exception hierarchy.

*Whether to retry.* A worker that retries everything turns a corrupt PDF into
twenty minutes of identical failures and a queue that never drains; one that
retries nothing turns a two-second Qdrant blip into a document an operator has
to notice and re-run by hand. The distinction is a property of the error, not of
the caller, so it is declared on the exception.

*What to call it.* ``error_code`` reaches the control room and, eventually, a
person deciding whether to re-upload. It is a closed vocabulary rather than a
stringified exception, so the same problem reads the same way every time and the
message is free to carry operational detail without becoming the identifier.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Every way ingestion can end badly. Stable — these are stored on job rows."""

    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    INVALID_DOCUMENT = "INVALID_DOCUMENT"
    CONTENT_HASH_MISMATCH = "CONTENT_HASH_MISMATCH"
    PDF_EXTRACTION_FAILED = "PDF_EXTRACTION_FAILED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    EMBEDDING_DIMENSION_MISMATCH = "EMBEDDING_DIMENSION_MISMATCH"
    VECTOR_STORE_UNAVAILABLE = "VECTOR_STORE_UNAVAILABLE"
    INDEXING_FAILED = "INDEXING_FAILED"
    CALLBACK_FAILED = "CALLBACK_FAILED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    INGESTION_FAILED = "INGESTION_FAILED"


class IngestionError(Exception):
    """Base for anything that ends an ingestion run.

    ``retryable`` is the whole point of the class. It is set by the subclass
    rather than by the code raising it, because whether a failure is worth
    trying again is a property of what went wrong — and a decision that would
    otherwise be re-made, differently, at every raise site.
    """

    code: ErrorCode = ErrorCode.INGESTION_FAILED
    retryable: bool = False

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause

    def as_report(self) -> dict[str, str]:
        """The two fields that reach the job row. Never the traceback."""
        return {"error_code": str(self.code), "error_message": self.message[:2000]}


# --- permanent: trying again produces the same result -----------------------


class DocumentNotFound(IngestionError):
    """The file the version points at is not in storage."""

    code = ErrorCode.DOCUMENT_NOT_FOUND


class InvalidDocument(IngestionError):
    """Readable, but not something this pipeline can index — no extractable
    text, an unsupported format, an empty file."""

    code = ErrorCode.INVALID_DOCUMENT


class ContentHashMismatch(IngestionError):
    """The bytes in storage are not the bytes the version was created from.

    Permanent on purpose: retrying reads the same wrong file. Something has
    replaced a version's content in place, which the model forbids, so the
    right outcome is a loud failure rather than an index that silently
    describes different content from the record pointing at it.
    """

    code = ErrorCode.CONTENT_HASH_MISMATCH


class PdfExtractionFailed(IngestionError):
    code = ErrorCode.PDF_EXTRACTION_FAILED


class EmbeddingDimensionMismatch(IngestionError):
    """The vectors produced do not fit the collection they are bound for.

    Never recoverable by retry and never worth working around: padding or
    truncating a vector produces a number that is not a distance, and every
    answer computed from it is confidently wrong.
    """

    code = ErrorCode.EMBEDDING_DIMENSION_MISMATCH


class InvalidPayload(IngestionError):
    """The message does not describe a job this worker can run."""

    code = ErrorCode.INVALID_PAYLOAD


class InvalidConfiguration(IngestionError):
    code = ErrorCode.INVALID_CONFIGURATION


# --- transient: the same call may well succeed shortly ----------------------


class EmbeddingFailed(IngestionError):
    """The embedding provider failed in a way that may pass on a retry."""

    code = ErrorCode.EMBEDDING_FAILED
    retryable = True


class VectorStoreUnavailable(IngestionError):
    code = ErrorCode.VECTOR_STORE_UNAVAILABLE
    retryable = True


class IndexingFailed(IngestionError):
    code = ErrorCode.INDEXING_FAILED
    retryable = True


class CallbackFailed(IngestionError):
    """The backend could not be told what happened.

    Retryable, and the reason the whole task is retried rather than only the
    callback: a run whose result never reached Django is a run whose result does
    not exist, however much work it did.
    """

    code = ErrorCode.CALLBACK_FAILED
    retryable = True


def classify(exc: BaseException) -> IngestionError:
    """Wrap an arbitrary exception as an IngestionError.

    Anything not already classified is treated as permanent. That is the safe
    default: an unknown failure retried three times is three identical
    tracebacks and a delayed answer, where an unknown failure reported once is
    a job an operator can look at.
    """
    if isinstance(exc, IngestionError):
        return exc
    if isinstance(exc, TimeoutError | ConnectionError):
        return VectorStoreUnavailable(f"{type(exc).__name__}: {exc}", cause=exc)
    return IngestionError(f"{type(exc).__name__}: {exc}", cause=exc)
