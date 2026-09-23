"""How much the gathered evidence actually supports an answer.

The score this replaces was a weighted blend of cosine similarities. Its problem
was not that the weights were wrong; it was that similarity answers a different
question. A retriever returning five passages that all closely resemble the
query is confident that it found *something related*, which is not the same as
having found *the answer* — and on a corpus of lift brochures, where every
document resembles every lift question, it is confident almost always.

So five signals are measured instead, each answering a question similarity
cannot:

    retrieval    how strong is the best passage?
    reranking    did the cross-encoder agree, or is one passage carrying it?
    agreement    do several independent sources say it?
    coverage     do the passages contain the things the question asked about?
    citation     did the finished answer actually rest on them?

Coverage is the one that earns its place most often. A question asking about
capacity *and* pit depth, answered from passages that only mention capacity, is
a half-answered question that every similarity-based score rates highly — and
the visitor cannot tell, because the half that was answered is answered well.

Citation support cannot be known before generation, so scoring happens in two
passes: :func:`assess` before, and :func:`with_citation_support` after. The
answer is generated from the first; the number reported to the client comes from
the second.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from app.core.constants import ConfidenceLevel
from app.orchestration.evidence import EvidenceBundle
from app.query_router.intents import Intent
from app.retrieval.confidence import normalize
from app.retrieval.sparse import tokenize

# Weights over the five components. Retrieval and reranking dominate because
# they are measurements of the evidence itself; coverage is a check on the
# question; agreement is corroboration, which is valuable but easy to fake with
# a corpus containing four copies of one brochure.
_WEIGHTS: Final[dict[str, float]] = {
    "retrieval": 0.30,
    "reranking": 0.20,
    "agreement": 0.15,
    "coverage": 0.20,
    "citation": 0.15,
}

# Before generation the citation component is unknown. Rather than scoring it
# zero — which would drag every pre-generation assessment below the refusal
# threshold — its weight is redistributed across the other four.
_PRE_GENERATION_SCALE: Final = 1.0 / (1.0 - _WEIGHTS["citation"])

# Terms too common in this domain to indicate that a passage is on topic. A
# passage containing "lift" has not covered a question about lifts.
_COVERAGE_STOPWORDS: Final[frozenset[str]] = frozenset(
    "lift lifts elevator elevators zion you your we our do does can please tell "
    "me about it they them".split()
)


@dataclass(slots=True, frozen=True)
class ConfidenceComponents:
    """The five measurements, each 0..1, kept for logging and diagnosis."""

    retrieval: float = 0.0
    reranking: float = 0.0
    agreement: float = 0.0
    coverage: float = 0.0
    citation: float = 0.0

    def as_fields(self) -> dict[str, float]:
        return {
            "confidence_retrieval": round(self.retrieval, 3),
            "confidence_reranking": round(self.reranking, 3),
            "confidence_agreement": round(self.agreement, 3),
            "confidence_coverage": round(self.coverage, 3),
            "confidence_citation": round(self.citation, 3),
        }


@dataclass(slots=True, frozen=True)
class EvidenceConfidence:
    """A level, the score behind it, and the reason in one phrase."""

    score: float
    level: ConfidenceLevel
    components: ConfidenceComponents = field(default_factory=ConfidenceComponents)
    reason: str = ""

    @property
    def is_high(self) -> bool:
        return self.level is ConfidenceLevel.HIGH

    @property
    def is_low(self) -> bool:
        return self.level is ConfidenceLevel.LOW


def _retrieval_component(bundle: EvidenceBundle) -> float:
    """The strongest single piece of evidence, normalised."""
    if not bundle.items:
        return 0.0
    return max(normalize(item.score) for item in bundle.items)


def _reranking_component(bundle: EvidenceBundle) -> float:
    """Whether the shortlist is uniformly good or held up by one passage.

    The mean of the top three rather than of all of them: a fifth passage is
    expected to be weaker and should not be read as the reranker disagreeing
    with itself.
    """
    scores = sorted((normalize(i.score) for i in bundle.items), reverse=True)[:3]
    return sum(scores) / len(scores) if scores else 0.0


def _agreement_component(bundle: EvidenceBundle) -> float:
    """Independent corroboration, counted by source rather than by passage.

    A website page agreeing with a document is worth more than a second chunk of
    the same document, so the website contributes its own increment. Three
    independent sources saturate it — beyond that, more agreement does not make
    a claim meaningfully safer.
    """
    documents = bundle.distinct_documents
    score = min(documents / 3.0, 1.0)
    if bundle.website and documents:
        score = min(score + 0.25, 1.0)
    elif bundle.website:
        # Website alone is authoritative for what the site says, which is what
        # navigational and contact questions are asking about.
        score = max(score, 0.5)
    return score


def _coverage_component(question: str, bundle: EvidenceBundle) -> float:
    """The share of the question's content words the evidence actually contains.

    Not a relevance measure — a measure of *completeness*. It is the signal that
    separates "answered" from "partly answered", which every score built on
    similarity alone treats identically.
    """
    wanted = {t for t in tokenize(question) if t not in _COVERAGE_STOPWORDS and len(t) > 2}
    if not wanted:
        return 1.0 if bundle.items else 0.0
    if not bundle.items:
        return 0.0

    present: set[str] = set()
    for item in bundle.items:
        present.update(tokenize(f"{item.title} {item.text}"))
    return len(wanted & present) / len(wanted)


def _band(score: float, high: float, low: float) -> tuple[ConfidenceLevel, str]:
    if score >= high:
        return ConfidenceLevel.HIGH, "well supported by several sources"
    if score >= low:
        return ConfidenceLevel.MEDIUM, "partial support; specifics may be missing"
    return ConfidenceLevel.LOW, "little supporting evidence"


def assess(
    question: str,
    bundle: EvidenceBundle,
    intent: Intent,
    high: float = 0.70,
    low: float = 0.35,
) -> EvidenceConfidence:
    """Score the evidence before an answer exists.

    ``intent`` matters because the bar is not the same for every question. A
    general engineering explanation needs no evidence at all — its confidence
    describes the optional supporting material, not the answer — so it is never
    reported as LOW purely for having retrieved nothing. A company question with
    no evidence is LOW by definition, which is exactly the outcome that stops an
    invented claim.
    """
    components = ConfidenceComponents(
        retrieval=_retrieval_component(bundle),
        reranking=_reranking_component(bundle),
        agreement=_agreement_component(bundle),
        coverage=_coverage_component(question, bundle),
        citation=0.0,
    )

    raw = (
        _WEIGHTS["retrieval"] * components.retrieval
        + _WEIGHTS["reranking"] * components.reranking
        + _WEIGHTS["agreement"] * components.agreement
        + _WEIGHTS["coverage"] * components.coverage
    ) * _PRE_GENERATION_SCALE
    score = round(min(raw, 1.0), 4)

    if intent is Intent.GENERAL_LIFT_KNOWLEDGE and bundle.is_empty:
        # No evidence was asked for. Reporting LOW here would make the widget
        # apologise for an answer that is correct and complete.
        return EvidenceConfidence(
            score=0.6,
            level=ConfidenceLevel.MEDIUM,
            components=components,
            reason="general engineering knowledge, not company-specific",
        )

    level, reason = _band(score, high, low)
    return EvidenceConfidence(score=score, level=level, components=components, reason=reason)


def with_citation_support(
    confidence: EvidenceConfidence,
    cited: int,
    available: int,
    high: float = 0.70,
    low: float = 0.35,
) -> EvidenceConfidence:
    """Fold in what the finished answer actually cited.

    An answer that cited nothing while evidence was available is the shape of a
    hallucination — the model had sources and did not use them — so the score
    falls. An answer that cited most of what it was given is the opposite, and
    this is the only component that can tell them apart, because it is the only
    one computed after the model has spoken.
    """
    if available <= 0:
        return confidence

    ratio = min(cited / min(available, 3), 1.0)
    components = ConfidenceComponents(
        retrieval=confidence.components.retrieval,
        reranking=confidence.components.reranking,
        agreement=confidence.components.agreement,
        coverage=confidence.components.coverage,
        citation=ratio,
    )
    base = confidence.score / _PRE_GENERATION_SCALE
    score = round(min(base + _WEIGHTS["citation"] * ratio, 1.0), 4)
    level, reason = _band(score, high, low)
    if cited == 0:
        reason = "the answer did not rest on the retrieved sources"
    return EvidenceConfidence(score=score, level=level, components=components, reason=reason)


__all__ = [
    "ConfidenceComponents",
    "EvidenceConfidence",
    "assess",
    "with_citation_support",
]
