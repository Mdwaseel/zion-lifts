"""What a given request is allowed to retrieve from.

Until now the chat endpoint took ``collection`` and ``filters`` from the request
body and handed them to Qdrant unchanged, which made the index's own naming the
security boundary: anyone who could guess a collection name could read it, and
anyone could send a filter that matched everything.

``RetrievalScope`` replaces that. It is constructed on the server from the
caller's identity, never parsed from a request body, and it is the only thing
the pipeline accepts — so an endpoint that forgets to apply a permission cannot
express "search everything" by accident. It has to name a knowledge base, and
the filters it produces are built here rather than supplied.

The `permissions` set is carried but not yet interpreted; document-level access
control arrives with the ingestion pipeline. It is part of the signature now so
that adding it later does not change every call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.vectorstore.collections import ACTIVE_FIELD, CollectionNameBuilder


def _one_or_many(values: tuple[str, ...]) -> Any:
    """A single id stays an equality match so Qdrant uses the payload index
    directly; several become a set membership."""
    return values[0] if len(values) == 1 else list(values)


@dataclass(frozen=True, slots=True)
class RetrievalScope:
    """The corpus one request may see.

    Construct it with :meth:`for_knowledge_base` for anything knowledge-base
    scoped, or :meth:`legacy` for the single pre-knowledge-base collection.
    """

    knowledge_base_id: str | None = None
    document_ids: tuple[str, ...] = ()
    # Named versions, for the one caller that legitimately wants a specific
    # edition: an administrator inspecting history. Empty means the active
    # edition only, which is what every chat request gets.
    document_version_ids: tuple[str, ...] = ()
    permissions: frozenset[str] = field(default_factory=frozenset)
    # Set only by `legacy`. A caller-supplied collection name is not accepted
    # anywhere else, which is the whole point of this type.
    _collection: str | None = None

    @classmethod
    def for_knowledge_base(
        cls,
        knowledge_base_id: str,
        document_ids: tuple[str, ...] | list[str] | None = None,
        permissions: frozenset[str] | set[str] | None = None,
    ) -> RetrievalScope:
        if not knowledge_base_id:
            raise ValueError("knowledge_base_id is required")
        return cls(
            knowledge_base_id=str(knowledge_base_id),
            document_ids=tuple(document_ids or ()),
            permissions=frozenset(permissions or ()),
        )

    @classmethod
    def for_versions(
        cls,
        knowledge_base_id: str,
        document_version_ids: tuple[str, ...] | list[str],
        permissions: frozenset[str] | set[str] | None = None,
    ) -> RetrievalScope:
        """Search named versions, active or not.

        The one way to reach a superseded or still-indexing edition, and it
        exists for administrative history rather than for chat. It is a separate
        constructor rather than a flag so that reaching past the active version
        is always a deliberate act at the call site, and so that no request
        body can turn it on.
        """
        if not knowledge_base_id:
            raise ValueError("knowledge_base_id is required")
        if not document_version_ids:
            raise ValueError("at least one document_version_id is required")
        return cls(
            knowledge_base_id=str(knowledge_base_id),
            document_version_ids=tuple(str(v) for v in document_version_ids),
            permissions=frozenset(permissions or ()),
        )

    @classmethod
    def legacy(cls, collection: str) -> RetrievalScope:
        """The corpus indexed before knowledge bases existed.

        It has no knowledge_base_id in its payloads, so it cannot be filtered
        into — it is addressed by its configured collection name and nothing
        else. New content does not go here.
        """
        if not collection:
            raise ValueError("a legacy scope needs a collection name")
        return cls(_collection=collection)

    @property
    def is_legacy(self) -> bool:
        return self._collection is not None

    def collection_for(
        self,
        embedding_model: str,
        embedding_model_version: str,
        embedding_dimension: int | None = None,
    ) -> str:
        """The collection this scope reads from, for the given embedding."""
        if self._collection is not None:
            return self._collection
        assert self.knowledge_base_id is not None  # guaranteed by both constructors
        return CollectionNameBuilder.build(
            knowledge_base_id=self.knowledge_base_id,
            embedding_model=embedding_model,
            embedding_model_version=embedding_model_version,
            embedding_dimension=embedding_dimension,
        )

    def to_filters(self) -> dict[str, Any]:
        """The payload filter for this scope.

        Always includes ``active: true``. A knowledge base's collection holds
        every version of every document in it, including versions still being
        written, so the collection name alone is not a boundary — the flag is
        what keeps a half-written edition out of an answer, and what keeps the
        previous edition answering until the new one is complete.

        Empty for a legacy scope: that collection predates both fields, holds
        exactly one corpus, and filtering on a flag none of its points carry
        would return nothing at all.
        """
        if self.is_legacy:
            return {}

        filters: dict[str, Any] = {"knowledge_base_id": self.knowledge_base_id}

        if self.document_version_ids:
            # Named versions replace the active filter rather than adding to it:
            # asking for a specific edition and then excluding it for not being
            # active would return nothing and look like an empty corpus.
            filters["document_version_id"] = _one_or_many(self.document_version_ids)
        else:
            filters[ACTIVE_FIELD] = True

        if self.document_ids:
            filters["document_id"] = _one_or_many(self.document_ids)
        return filters

    def describe(self) -> dict[str, Any]:
        """Log-safe summary. Never includes the permission set."""
        return {
            "knowledge_base_id": self.knowledge_base_id,
            "documents": len(self.document_ids) or None,
            "versions": len(self.document_version_ids) or None,
            "legacy": self.is_legacy or None,
        }
