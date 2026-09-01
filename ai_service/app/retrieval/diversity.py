"""Choose a context set that says several things rather than one thing four times.

Reranking sorts by relevance, and relevance alone has a failure mode that is
easy to miss and expensive to keep: the top five passages are frequently five
views of the same paragraph. Chunking with overlap guarantees neighbours share
text; a product datasheet repeats its capacity table in three sections; a
brochure and its PDF export are two documents saying the same sentence. The
model then sees one fact stated five times, the context budget is spent, and the
second half of a two-part question has no evidence at all.

Maximal Marginal Relevance fixes exactly that. Each pick maximises

    lambda * relevance  -  (1 - lambda) * max similarity to what is already picked

so a passage has to be *both* relevant and different to earn a slot.

Similarity here is lexical — cosine over term counts — rather than embedding
based. Three reasons: the chunks reaching this stage have been scored by a cross
encoder that produces no vector, embedding them would add a model call to every
query, and near-duplicate detection is precisely the case where surface overlap
is the right signal. Two passages that share most of their words are the same
passage whatever an embedding thinks.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Final

from app.retrieval.sparse import tokenize
from app.vectorstore.base import ScoredChunk

#: How much of the objective is relevance. 0.7 keeps ranking firmly in charge —
#: diversity is a tie-breaker among comparable passages, not a reason to promote
#: an irrelevant one. At 0.5 the second pick starts being chosen for being
#: different rather than for being useful.
DEFAULT_LAMBDA: Final = 0.7

#: Above this, two passages are treated as the same passage and the weaker one
#: is dropped outright rather than merely penalised. Chunk overlap routinely
#: produces 0.8; genuinely distinct passages from one document rarely exceed it.
NEAR_DUPLICATE: Final = 0.92


def _terms(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def cosine(a: Counter[str], b: Counter[str]) -> float:
    """Cosine similarity over term counts. 0.0 when either side is empty."""
    if not a or not b:
        return 0.0
    shared = a.keys() & b.keys()
    if not shared:
        return 0.0
    dot = sum(a[t] * b[t] for t in shared)
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def _normalized_scores(chunks: list[ScoredChunk]) -> list[float]:
    """Scores mapped onto 0..1 within this result set.

    Min-max within the set rather than a global normalisation: MMR compares a
    relevance term against a similarity term, and similarity is already bounded
    at 0..1. Cross-encoder logits are not bounded at all, so without this the
    relevance term would dominate by orders of magnitude on some queries and be
    swamped on others.
    """
    if not chunks:
        return []
    scores = [float(c.score) for c in chunks]
    low, high = min(scores), max(scores)
    if high - low < 1e-9:
        return [1.0] * len(scores)
    return [(s - low) / (high - low) for s in scores]


def select_diverse(
    chunks: list[ScoredChunk],
    limit: int,
    lambda_: float = DEFAULT_LAMBDA,
    near_duplicate: float = NEAR_DUPLICATE,
) -> list[ScoredChunk]:
    """Pick ``limit`` passages that are relevant *and* not repetitive.

    Input order is assumed to be the ranking. The first pick is always the
    top-ranked passage — diversity has nothing to trade against yet, and
    starting anywhere else would mean the best answer to the question was
    displaced by a formula about variety.
    """
    if limit <= 0 or not chunks:
        return []
    if len(chunks) <= 1:
        return list(chunks[:limit])

    relevance = _normalized_scores(chunks)
    terms = [_terms(c.text) for c in chunks]

    chosen: list[int] = [0]
    remaining = set(range(1, len(chunks)))

    while remaining and len(chosen) < limit:
        best_index = -1
        best_value = -math.inf

        for index in remaining:
            worst = max(cosine(terms[index], terms[picked]) for picked in chosen)
            if worst >= near_duplicate:
                continue
            value = lambda_ * relevance[index] - (1.0 - lambda_) * worst
            if value > best_value:
                best_value, best_index = value, index

        if best_index < 0:
            # Everything left duplicates something already chosen. Returning
            # fewer passages is the right answer: padding the context with
            # restatements is the failure this function exists to prevent.
            break
        chosen.append(best_index)
        remaining.discard(best_index)

    return [chunks[i] for i in chosen]


def redundancy(chunks: list[ScoredChunk]) -> float:
    """Mean pairwise similarity of a set. 0.0 for fewer than two passages.

    Reported as a metric rather than used for a decision: it is the number that
    says whether the chunker's overlap or the corpus itself is producing
    repetitive context, and neither is visible from the answer.
    """
    if len(chunks) < 2:
        return 0.0
    terms = [_terms(c.text) for c in chunks]
    pairs = [
        cosine(terms[i], terms[j]) for i in range(len(terms)) for j in range(i + 1, len(terms))
    ]
    return round(sum(pairs) / len(pairs), 4) if pairs else 0.0


__all__ = ["DEFAULT_LAMBDA", "NEAR_DUPLICATE", "cosine", "redundancy", "select_diverse"]
