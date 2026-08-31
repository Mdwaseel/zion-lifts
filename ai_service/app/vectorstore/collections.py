"""Collection naming and payload-index definitions.

A collection name is not cosmetic — it is the compatibility boundary of the
index. Vectors from two different embedding models cannot be compared, and a
384-dimensional vector cannot even be written into a 768-dimensional collection,
so the model and its version are part of the name rather than a payload field
that nothing enforces. Changing either routes writes to a new collection and
leaves the old one intact and queryable, which is what makes a re-embedding
migration a background job instead of an outage.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.core.constants import DEFAULT_COLLECTION

# Payload fields that must be indexed for fast filtering in Qdrant. The first
# three are the retrieval scope; without indexes on those, every filtered search
# degrades to a scan.
KEYWORD_INDEXES: tuple[str, ...] = (
    "knowledge_base_id",
    "document_id",
    "document_version_id",
    "source_type",
    "tags",
    "language",
)

# Indexed separately because it is a boolean, not a keyword, and it is on the
# critical path of every single search.
BOOL_INDEXES: tuple[str, ...] = ("active",)

TEXT_FIELD = "text"
DOCUMENT_ID_FIELD = "document_id"
KNOWLEDGE_BASE_ID_FIELD = "knowledge_base_id"
DOCUMENT_VERSION_ID_FIELD = "document_version_id"

# Named vectors. A chunk carries both halves of hybrid retrieval in one point,
# so dense and sparse always agree about which chunk they are ranking and the
# fusion has a single identity to key on.
#
# Collections created before Phase 4 have one unnamed dense vector and no sparse
# vector at all. `QdrantVectorStore` detects that and queries them the old way;
# see `_layout_of` there.
DENSE_VECTOR = "dense"
SPARSE_VECTOR = "sparse"

# Whether a chunk belongs to the edition currently answering questions.
#
# This flag is what makes a partial index invisible. Chunks are written with
# `active=False` and flipped in a single server-side `set_payload` once the
# whole version has been indexed, so a run that dies at chunk 700 of 1000
# leaves 700 chunks nothing will ever retrieve — rather than 700 chunks that
# answer questions as if they were a whole document.
ACTIVE_FIELD = "active"

# Qdrant accepts more than this, but a name that is also a valid identifier
# everywhere (logs, dashboards, shell) is worth the narrower alphabet.
_UNSAFE = re.compile(r"[^a-z0-9]+")
_MAX_SEGMENT = 40


def _slug(value: str) -> str:
    return _UNSAFE.sub("_", str(value).strip().lower()).strip("_")[:_MAX_SEGMENT]


def _model_slug(value: str) -> str:
    """A model name as one safe, collision-free segment.

    Truncation is where a naming scheme quietly stops being safe: two long model
    names sharing a prefix would slug to the same thing and share a collection.
    When the name does not fit, a short digest of the *full* name is appended,
    so the segment stays readable and stays unique.
    """
    full = _UNSAFE.sub("_", str(value).strip().lower()).strip("_")
    if len(full) <= _MAX_SEGMENT:
        return full

    digest = hashlib.blake2b(value.strip().lower().encode("utf-8"), digest_size=3).hexdigest()
    return f"{full[: _MAX_SEGMENT - len(digest) - 1]}_{digest}"


@dataclass(frozen=True, slots=True)
class CollectionSpec:
    name: str
    vector_size: int
    distance: str = "Cosine"


class CollectionNameBuilder:
    """Builds `kb_<knowledge base>__<model>_<version>`.

    The double underscore separates the two halves of the name — what is being
    indexed, and what it was indexed *with* — so an operator scanning a list of
    collections can tell at a glance which ones are the same corpus under a
    different embedding.
    """

    PREFIX = "kb"
    SEPARATOR = "__"

    @classmethod
    def build(
        cls,
        knowledge_base_id: str,
        embedding_model: str,
        embedding_model_version: str,
        embedding_dimension: int | None = None,
    ) -> str:
        """`kb_<base>__<model>_<version>[_d<dim>]`.

        The dimension is in the name when it is known, and that is the last line
        of defence in a chain of them. Two models with different widths already
        get different names because their model segments differ — but a model
        *revision* that quietly changed width would otherwise collide with its
        own past, and the mismatch would surface as rejected upserts halfway
        through an ingestion rather than as a different collection.

        Omitted when unknown so that a name built before the dimension is
        available still resolves to the same collection.
        """
        base = _slug(knowledge_base_id)
        if not base:
            raise ValueError("knowledge_base_id is required to name a collection")

        # The *whole* model name, organisation included. Taking only the segment
        # after the slash reads better and is wrong: `org-a/embed` and
        # `org-b/embed` are different models producing incomparable vectors, and
        # they would have shared a collection. Two geometries in one index is
        # the failure this naming exists to prevent, so the name keeps
        # everything that distinguishes one model from another.
        model = _model_slug(embedding_model)
        version = _slug(embedding_model_version) or "v1"
        if not model:
            raise ValueError("embedding_model is required to name a collection")

        name = f"{cls.PREFIX}_{base}{cls.SEPARATOR}{model}_{version}"
        if embedding_dimension:
            name = f"{name}_d{int(embedding_dimension)}"
        return name

    @classmethod
    def is_generated(cls, name: str) -> bool:
        """Whether a name came from this builder rather than from configuration."""
        return name.startswith(f"{cls.PREFIX}_") and cls.SEPARATOR in name


def resolve(name: str | None, default: str = DEFAULT_COLLECTION) -> str:
    """Pick the caller's collection, falling back to the configured default.

    Retained for the pre-knowledge-base corpus, which lives in one collection
    named in configuration. Anything scoped to a knowledge base is named by
    ``CollectionNameBuilder`` instead — see ``RetrievalScope.collection_for``.
    """
    return (name or default).strip() or default


def spec_for(name: str, vector_size: int) -> CollectionSpec:
    return CollectionSpec(name=name, vector_size=vector_size)
