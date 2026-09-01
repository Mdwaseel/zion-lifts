"""Ranking metrics, computed the standard way and reported honestly.

Nothing here invents a number. A metric that cannot be computed from the labels
present returns ``None`` rather than 0.0, because the two are not the same
statement and a dashboard cannot tell them apart afterwards: 0.0 means "we
looked and found nothing", ``None`` means "there was nothing to look for".

The four are the usual ones, and each answers a different question:

    precision@k   of what we showed, how much was right?
    recall@k      of what was right, how much did we show?
    MRR           how far down was the first right answer?
    NDCG@k        were the right answers near the top, or merely present?
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def precision_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float | None:
    """Share of the top k that is relevant."""
    if not relevant:
        return None
    top = list(retrieved[:k])
    if not top:
        return 0.0
    wanted = set(relevant)
    return sum(1 for item in top if item in wanted) / len(top)


def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float | None:
    """Share of the relevant set that made it into the top k."""
    if not relevant:
        return None
    wanted = set(relevant)
    found = {item for item in retrieved[:k] if item in wanted}
    return len(found) / len(wanted)


def reciprocal_rank(retrieved: Sequence[str], relevant: Sequence[str]) -> float | None:
    """1/rank of the first relevant result, or 0.0 if none appeared.

    The metric that matters most for a chat assistant: the model reads the
    context from the top, and a correct passage at rank nine is frequently a
    correct passage that did not fit in the budget.
    """
    if not relevant:
        return None
    wanted = set(relevant)
    for index, item in enumerate(retrieved, start=1):
        if item in wanted:
            return 1.0 / index
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float | None:
    """Discounted gain against the best possible ordering.

    Binary relevance, because the dataset labels documents as relevant or not
    rather than on a scale. Graded relevance would be more informative and would
    also be a judgement call per document, which is exactly the kind of label
    that quietly becomes whatever makes the current system look good.
    """
    if not relevant:
        return None
    wanted = set(relevant)
    gains = [1.0 if item in wanted else 0.0 for item in retrieved[:k]]
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))
    ideal_hits = min(len(wanted), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def mean(values: Sequence[float | None]) -> float | None:
    """Average of the values that exist. ``None`` if none of them do."""
    present = [v for v in values if v is not None]
    return round(sum(present) / len(present), 4) if present else None


__all__ = ["mean", "ndcg_at_k", "precision_at_k", "recall_at_k", "reciprocal_rank"]
