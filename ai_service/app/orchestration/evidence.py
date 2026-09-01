"""What was gathered for one question, and where each piece came from.

The type that makes the answer policy enforceable. Retrieved chunks and website
pages arrive from different subsystems with different guarantees, and the whole
"never claim Zion does X without a source" rule depends on the generator being
able to tell which is which — so they are never flattened into a list of
strings. Every piece of evidence carries its origin, keeps its own citation
number, and knows whether it may support a claim about the company.

The numbering deserves a note. Citation markers are assigned *here*, once,
across both kinds of evidence, so ``[1]`` means the same passage in the prompt,
in the answer, and in the citation list the browser renders. Numbering documents
and pages separately — or renumbering after generation — is how a citation ends
up pointing at the wrong source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.vectorstore.base import ScoredChunk
from app.website.models import WebsitePage


class EvidenceKind(StrEnum):
    """Where a piece of evidence came from, and therefore what it can support."""

    #: An ingested document. The strongest support for a company claim.
    DOCUMENT = "document"
    #: A page of the company's own website. Authoritative for navigation,
    #: contact details and the published catalogue.
    WEBSITE = "website"


@dataclass(slots=True, frozen=True)
class EvidenceItem:
    """One numbered passage, with everything needed to cite it."""

    marker: int
    kind: EvidenceKind
    title: str
    text: str
    score: float
    #: Set for DOCUMENT evidence.
    chunk_id: str = ""
    document_id: str = ""
    source: str | None = None
    #: Set for WEBSITE evidence. Always a route this service has verified.
    url: str | None = None
    section: str | None = None
    #: True when injection scanning found something in this passage and it was
    #: rewritten before being shown to the model.
    sanitized: bool = False

    @property
    def label(self) -> str:
        """How the passage is introduced to the model."""
        if self.kind is EvidenceKind.WEBSITE:
            where = f"{self.title} — {self.section}" if self.section else self.title
            return f"{where} ({self.url})"
        return f"{self.title} ({self.source})" if self.source else self.title


@dataclass(slots=True)
class EvidenceBundle:
    """Everything gathered for one question.

    Mutable during collection and read-only in spirit afterwards. It is passed
    to confidence scoring, to prompt assembly and to citation building, and each
    of those reads a different part of it — which is the reason it is one object
    rather than three parallel lists that could fall out of step.
    """

    items: list[EvidenceItem] = field(default_factory=list)
    #: The reranked chunks, kept alongside the numbered items because retrieval
    #: diagnostics (scores, metadata, the /search endpoint) want the originals.
    chunks: list[ScoredChunk] = field(default_factory=list)
    #: Pages worth offering as links. A superset of the pages cited: a page can
    #: be a good destination without having supported a claim.
    pages: list[tuple[WebsitePage, str | None, float]] = field(default_factory=list)
    #: Sources that were asked for but returned nothing, by name. Reported so a
    #: rising rate of "rag returned nothing" is visible rather than inferred.
    empty_sources: tuple[str, ...] = ()
    #: True when at least one passage had to be neutralised.
    sanitized_any: bool = False

    @property
    def is_empty(self) -> bool:
        return not self.items

    @property
    def documents(self) -> list[EvidenceItem]:
        return [i for i in self.items if i.kind is EvidenceKind.DOCUMENT]

    @property
    def website(self) -> list[EvidenceItem]:
        return [i for i in self.items if i.kind is EvidenceKind.WEBSITE]

    @property
    def distinct_documents(self) -> int:
        """How many different source documents support this answer.

        Chunks from one PDF agreeing with each other is not corroboration — it
        is one source said four times — so this counts documents, not passages.
        """
        return len({i.document_id for i in self.documents if i.document_id})

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item)
        if item.sanitized:
            self.sanitized_any = True

    def describe(self) -> dict[str, object]:
        """Log-safe counts."""
        return {
            "evidence_items": len(self.items),
            "evidence_documents": len(self.documents),
            "evidence_pages": len(self.website),
            "distinct_documents": self.distinct_documents,
            "sanitized": self.sanitized_any or None,
            "empty_sources": ",".join(self.empty_sources) or None,
        }


__all__ = ["EvidenceBundle", "EvidenceItem", "EvidenceKind"]
