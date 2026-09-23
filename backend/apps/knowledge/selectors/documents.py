"""Read queries for documents and their jobs.

Separate from the services so that reading is obviously free of side effects,
and so the joins each view needs live next to each other rather than being
rediscovered — every list below is written to be one query, not N.
"""

from __future__ import annotations

from django.db.models import QuerySet

from ..models import Document, DocumentVersion, IngestionJob
from ..states import IN_FLIGHT, DocumentState


def documents(knowledge_base_id=None) -> QuerySet[Document]:
    """Documents, newest first, ready to list without further queries."""
    queryset = Document.objects.select_related("knowledge_base", "active_version")
    if knowledge_base_id is not None:
        queryset = queryset.filter(knowledge_base_id=knowledge_base_id)
    return queryset


def searchable(knowledge_base_id=None) -> QuerySet[Document]:
    """Documents whose live edition can currently answer a question.

    An active version alone is not enough — the knowledge base has to be active
    too, or deactivating one would leave its documents quietly answerable.
    """
    return (
        documents(knowledge_base_id)
        .filter(
            status=DocumentState.READY,
            active_version__isnull=False,
            knowledge_base__is_active=True,
        )
    )


def in_progress() -> QuerySet[Document]:
    """Everything currently being worked on, for the control room's header."""
    return documents().filter(status__in=IN_FLIGHT)


def failed() -> QuerySet[Document]:
    return documents().filter(status=DocumentState.FAILED)


def versions(document: Document) -> QuerySet[DocumentVersion]:
    """Editions of one document, newest first."""
    return document.versions.all()


def jobs(document: Document | None = None) -> QuerySet[IngestionJob]:
    queryset = IngestionJob.objects.select_related("document", "document_version")
    if document is not None:
        queryset = queryset.filter(document=document)
    return queryset


def latest_job(document: Document) -> IngestionJob | None:
    return jobs(document).first()


def version_by_file(reference: str) -> DocumentVersion | None:
    """The version whose stored file is ``reference``, if any.

    Used by the internal file route so the worker can only ever read files this
    app created. Matching against a real row is what keeps the reference from
    being a path into MEDIA_ROOT: an arbitrary string finds nothing.
    """
    if not reference:
        return None
    return (
        DocumentVersion.objects.select_related("document")
        .filter(file=reference.strip())
        .first()
    )
