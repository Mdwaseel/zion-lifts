"""Read queries for knowledge bases."""

from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from ..models import KnowledgeBase
from ..states import DocumentState


def all_bases() -> QuerySet[KnowledgeBase]:
    return KnowledgeBase.objects.all()


def active() -> QuerySet[KnowledgeBase]:
    """The bases a question may be answered from."""
    return KnowledgeBase.objects.filter(is_active=True)


def with_counts() -> QuerySet[KnowledgeBase]:
    """Bases annotated with what is in them.

    Two numbers rather than one, because they answer different questions: how
    much has been uploaded, and how much of it is actually answerable. A base
    where those diverge is a base with a problem.
    """
    return KnowledgeBase.objects.annotate(
        document_count=Count("documents", distinct=True),
        ready_count=Count(
            "documents",
            filter=Q(documents__status=DocumentState.READY),
            distinct=True,
        ),
    )


def by_slug(slug: str) -> KnowledgeBase | None:
    return KnowledgeBase.objects.filter(slug=slug).first()
