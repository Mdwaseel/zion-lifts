"""The document lifecycle, as operations rather than as HTTP.

Views call these; nothing here knows what a request is. Each function is one
thing an operator does — upload a document, replace it, reindex it, retry it,
delete it — and each leaves the records and the queue consistent with each
other, because the alternative is a control room that shows a state the index
does not have.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Document, DocumentVersion, IngestionJob, JobType, KnowledgeBase
from ..states import DocumentState, InvalidTransition
from ..validators import validate_upload
from . import job_service, version_service

log = logging.getLogger(__name__)


class DuplicateContent(ValidationError):
    """These exact bytes are already an edition of this document.

    A subclass of ValidationError so the API layer reports it as a 400 with a
    message, but distinguishable so a caller that wants to reindex the existing
    version instead can catch it.
    """

    def __init__(self, version: DocumentVersion) -> None:
        self.version = version
        super().__init__(
            f"That file is byte-for-byte version {version.version_number} of this "
            "document, which is already stored. Reindex that version instead of "
            "uploading it again."
        )


@transaction.atomic
def create_document(
    *,
    knowledge_base: KnowledgeBase,
    upload,
    name: str = "",
    created_by=None,
    queue_ingestion: bool = True,
) -> tuple[Document, DocumentVersion, IngestionJob | None]:
    """Accept an uploaded file as a new document and queue its first ingestion.

    The file is validated and hashed here, in the request, and parsed nowhere:
    a Django worker must not be holding a connection open while a 300-page scan
    is read. Everything past storage happens in the background.
    """
    facts = validate_upload(upload)

    document = Document.objects.create(
        knowledge_base=knowledge_base,
        name=(name or facts["filename"]).strip()[:200],
        original_filename=facts["filename"],
        mime_type=facts["mime_type"],
        file_size=facts["file_size"],
        status=DocumentState.UPLOADED,
        created_by=created_by,
    )
    version = version_service.create_version(
        document,
        upload=upload,
        content_hash=facts["content_hash"],
        file_size=facts["file_size"],
    )

    job = job_service.queue(version, job_type=JobType.INGEST) if queue_ingestion else None
    log.info(
        "document created",
        extra={
            "document_id": str(document.id),
            "knowledge_base_id": str(knowledge_base.id),
            "version": version.version_number,
        },
    )
    return document, version, job


@transaction.atomic
def add_version(
    document: Document,
    *,
    upload,
    queue_ingestion: bool = True,
    allow_duplicate: bool = False,
) -> tuple[DocumentVersion, IngestionJob | None]:
    """Store a replacement edition of an existing document.

    Identical bytes are refused rather than stored. Re-uploading the same file
    is nearly always a repeated click or a retry, and honouring it would mean a
    second copy of every chunk in the index, a second embedding bill, and two
    versions an operator then has to tell apart. ``allow_duplicate`` exists for
    the case where the bytes really are meant to be re-processed — a change in
    chunking, or an index that was lost.
    """
    facts = validate_upload(upload)

    if not allow_duplicate:
        existing = version_service.find_by_content(document, facts["content_hash"])
        if existing is not None:
            raise DuplicateContent(existing)

    version = version_service.create_version(
        document,
        upload=upload,
        content_hash=facts["content_hash"],
        file_size=facts["file_size"],
    )
    # The document's own metadata follows the newest upload; the previous
    # edition keeps serving until this one is indexed.
    document.original_filename = facts["filename"]
    document.mime_type = facts["mime_type"]
    document.file_size = facts["file_size"]
    document.save(update_fields=["original_filename", "mime_type", "file_size", "updated_at"])

    job = job_service.queue(version, job_type=JobType.INGEST) if queue_ingestion else None
    return version, job


def reindex(document: Document, *, version: DocumentVersion | None = None) -> IngestionJob:
    """Re-run ingestion for an edition that is already stored.

    Safe to call repeatedly: the job layer returns an in-flight job rather than
    starting a second one, and the worker writes deterministic chunk ids, so a
    second pass over the same version overwrites its own chunks instead of
    adding a duplicate set.
    """
    target = version or document.active_version or document.versions.first()
    if target is None:
        raise ValidationError("That document has no stored version to reindex.")
    return job_service.queue(target, job_type=JobType.REINDEX)


def retry(document: Document) -> IngestionJob:
    """Try a failed document again, from its most recent edition."""
    if document.status != DocumentState.FAILED:
        raise InvalidTransition(document.status, DocumentState.PROCESSING)

    target = document.versions.first()  # ordering is -version_number
    if target is None:
        raise ValidationError("That document has no stored version to retry.")
    return job_service.queue(target, job_type=JobType.INGEST, force=True)


@transaction.atomic
def request_deletion(document: Document) -> IngestionJob:
    """Begin removing a document and its vectors.

    The record is not deleted here. It moves to DELETING and a job is queued to
    clear the index first, because a row removed before its chunks are gone
    leaves vectors nothing can ever identify or reclaim.
    """
    target = document.active_version or document.versions.first()
    document.transition_to(DocumentState.DELETING)

    if target is None:
        # Nothing was ever indexed, so there is nothing for a worker to clear.
        document.transition_to(DocumentState.DELETED)
        return IngestionJob.objects.create(
            document=document,
            job_type=JobType.DELETE,
            status="succeeded",
            progress=100,
        )

    return job_service.queue(target, job_type=JobType.DELETE, force=True)
