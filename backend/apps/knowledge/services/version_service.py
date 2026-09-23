"""Creating and finishing document versions."""

from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models import Max

from ..models import Document, DocumentVersion
from ..states import DocumentState


def next_version_number(document: Document) -> int:
    """The number the next edition gets.

    Read inside the caller's transaction, and backed by the unique constraint on
    ``(document, version_number)``: two simultaneous uploads can both compute
    the same number, and the second insert is what fails, not the data.
    """
    highest = document.versions.aggregate(n=Max("version_number"))["n"]
    return (highest or 0) + 1


@transaction.atomic
def create_version(
    document: Document,
    *,
    upload,
    content_hash: str,
    file_size: int,
) -> DocumentVersion:
    """Store an uploaded file as the next edition of ``document``.

    The embedding model is stamped at creation from current configuration
    rather than read at index time. That is what makes the record honest later:
    if the service's model changes next month, this version still says what it
    was actually built with, and the mismatch is visible instead of assumed.
    """
    version = DocumentVersion(
        document=document,
        version_number=next_version_number(document),
        content_hash=content_hash,
        file_size=file_size,
        status=DocumentState.UPLOADED,
        embedding_model=getattr(settings, "AI_EMBEDDING_MODEL", ""),
        embedding_model_version=getattr(settings, "AI_EMBEDDING_MODEL_VERSION", ""),
    )
    # Assigned after construction so `document_upload_path` can read the version
    # number it is being filed under.
    version.file = upload
    version.save()
    return version


def find_by_content(document: Document, content_hash: str) -> DocumentVersion | None:
    """An existing edition of this document with identical bytes, if any."""
    return document.versions.filter(content_hash=content_hash).order_by("-version_number").first()


@transaction.atomic
def complete_version(
    version: DocumentVersion,
    *,
    page_count: int | None = None,
    chunk_count: int | None = None,
    embedding_dimension: int | None = None,
    collection: str = "",
    embedding_model: str = "",
    embedding_model_version: str = "",
) -> DocumentVersion:
    """Record a successful index and make this edition the live one.

    The embedding identity is overwritten with what the worker actually used,
    not left at what was stamped at upload. If a fallback provider answered, the
    version must say so — the collection it was written to is named after that
    model, and a record naming a different one would point at an index that does
    not hold this version's vectors.
    """
    version.transition_to(DocumentState.READY, save=False)
    version.page_count = page_count
    version.chunk_count = chunk_count
    version.embedding_dimension = embedding_dimension
    version.collection = collection
    if embedding_model:
        version.embedding_model = embedding_model
    if embedding_model_version:
        version.embedding_model_version = embedding_model_version
    version.error_code = ""
    version.error_message = ""
    version.save()

    version.document.publish_version(version)
    return version


@transaction.atomic
def fail_version(version: DocumentVersion, *, code: str, message: str = "") -> DocumentVersion:
    """Record a failed index without disturbing the edition currently serving.

    The document only follows the version into FAILED when it has nothing else
    to answer from. A failed re-index of a document that already has a live
    version is a failed *job*, not a broken document, and marking it otherwise
    would hide a working corpus behind a red status.
    """
    # Idempotent. A version already marked failed is not an error to record
    # again — a redelivered failure report, or a second handover that also
    # could not reach the broker, should refresh the reason and leave the
    # lifecycle alone rather than raising from inside an on-commit callback.
    if version.status != DocumentState.FAILED:
        version.transition_to(DocumentState.FAILED, save=False)
    version.error_code = code[:80]
    version.error_message = message[:4000]
    version.save()

    document = version.document
    if document.active_version_id is None and document.status != DocumentState.FAILED:
        document.transition_to(DocumentState.FAILED)
    return version
