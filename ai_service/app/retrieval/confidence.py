"""Turn retrieval signals into a single answerability score."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import CONFIDENCE_HIGH, CONFIDENCE_LOW, ConfidenceLevel
from app.vectorstore.base import ScoredChunk


def _sigmoid(x: float) -> float:
    from math import exp

    return 1.0 / (1.0 + exp(-x))


def normalize(score: float) -> float:
    """Cross-encoder logits are unbounded; cosine similarity is already 0..1."""
    if 0.0 <= score <= 1.0:
        return score
    return _sigmoid(score)


@dataclass(slots=True)
class ConfidenceReport:
    score: float
    level: ConfidenceLevel
    top_score: float
    mean_score: float
    agreement: float
    reason: str

    @property
    def should_answer(self) -> bool:
        return self.level is not ConfidenceLevel.LOW


def assess(
    chunks: list[ScoredChunk],
    min_chunks: int = 1,
    high: float = CONFIDENCE_HIGH,
    low: float = CONFIDENCE_LOW,
) -> ConfidenceReport:
    """Combine top relevance, support depth and source agreement.

    A single strong chunk is weaker evidence than several agreeing ones, so
    agreement across distinct documents is folded into the score.

    ``high`` and ``low`` default to the module constants and are supplied from
    ``Settings`` in the running service — the band between them decides whether
    an answer is generated at all, which is not a number that should need a
    deploy to change.
    """
    if len(chunks) < min_chunks or not chunks:
        return ConfidenceReport(0.0, ConfidenceLevel.LOW, 0.0, 0.0, 0.0, "no relevant context")

    scores = [normalize(c.score) for c in chunks]
    top = max(scores)
    mean = sum(scores) / len(scores)

    documents = {c.document_id for c in chunks if c.document_id}
    agreement = min(len(documents) / 3.0, 1.0) if documents else 0.0

    score = round(0.6 * top + 0.25 * mean + 0.15 * agreement, 4)

    if score >= high:
        level, reason = ConfidenceLevel.HIGH, "strong, well-supported match"
    elif score >= low:
        level, reason = ConfidenceLevel.MEDIUM, "partial support in the corpus"
    else:
        level, reason = ConfidenceLevel.LOW, "weak match; answer may not be grounded"

    return ConfidenceReport(
        score=score,
        level=level,
        top_score=round(top, 4),
        mean_score=round(mean, 4),
        agreement=round(agreement, 4),
        reason=reason,
    )
