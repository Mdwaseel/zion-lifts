"""Turning text into a sparse vector Qdrant can search natively.

The lexical half of retrieval used to work by scrolling up to two thousand
chunks out of Qdrant and building a BM25 index over them, per query. That is
linear in corpus size on every request, and it truncates: past the scan limit,
recall silently stops improving no matter how relevant the missing chunks are.

Qdrant indexes sparse vectors itself, so the work belongs there. This module is
the small piece that has to stay on this side — deciding which dimensions a
piece of text occupies and how strongly.

**Term frequency here, IDF in Qdrant.** The collection declares
``Modifier.IDF``, so the server computes inverse document frequency across the
whole collection at query time and multiplies it in. That is the half that
genuinely needs corpus-wide knowledge, and the half a client cannot compute
without reading the corpus — which is exactly what we are getting rid of.

**Log saturation rather than raw counts.** A term appearing twelve times does
not make a chunk twelve times more relevant. Full BM25 length normalisation
needs the average document length across the collection, which is corpus-wide
knowledge again; ``log(1 + tf)`` gets most of the benefit from information
available locally, and is deterministic.

**Hashed dimensions.** A term's index is the first four bytes of its BLAKE2
digest. Python's own ``hash()`` is salted per process, so a term would land in a
different dimension in the worker than in the API — the index would be built in
one space and queried in another, and every lexical search would silently return
nothing.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

# Deliberately the same tokenizer the previous BM25 implementation used, so the
# behaviour that was tested carries over rather than being reinvented.
_TOKEN = re.compile(r"[a-z0-9_]+")

_STOPWORDS = frozenset(
    "a an and are as at be by for from has have how in is it its of on or that "
    "the then there these this to was were what when where which who why will "
    "with".split()
)

# Qdrant sparse indices are unsigned 32-bit. With a vocabulary in the hundreds
# of thousands, collisions in that space are rare enough to be noise in the
# ranking rather than a correctness problem.
_INDEX_SPACE = 2**32


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, minus stopwords and single characters."""
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def term_index(term: str) -> int:
    """The sparse dimension a term occupies.

    Stable across processes, machines and restarts — which the built-in ``hash``
    is not. An index built by the worker has to be queryable by the API.
    """
    digest = hashlib.blake2b(term.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") % _INDEX_SPACE


@dataclass(frozen=True, slots=True)
class SparseText:
    """One text as sparse coordinates. Empty when nothing survived tokenising."""

    indices: list[int]
    values: list[float]

    @property
    def is_empty(self) -> bool:
        return not self.indices

    def as_dict(self) -> dict[str, list]:
        return {"indices": self.indices, "values": self.values}


class SparseEncoder:
    """Text to sparse vector. Stateless, deterministic, and corpus-independent.

    Corpus-independent is the important property: the encoder never needs to
    know what else is in the collection, so the worker can encode a chunk at
    ingestion time and the API can encode a query months later and the two still
    line up.
    """

    def __init__(self, max_terms: int = 512) -> None:
        # A cap on how many distinct terms one chunk contributes. A pathological
        # document — a word list, an index page — would otherwise produce a
        # vector dense enough to be slow to score and useless to rank with.
        self._max_terms = max_terms

    def encode(self, text: str) -> SparseText:
        counts = Counter(tokenize(text))
        if not counts:
            return SparseText(indices=[], values=[])

        # Keep the strongest terms when a chunk is unusually rich. Ties break on
        # the term itself so the result does not depend on dict ordering.
        if len(counts) > self._max_terms:
            ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
            counts = Counter(dict(ranked[: self._max_terms]))

        # Collisions are folded together rather than overwriting: two terms
        # sharing a dimension should sum, the same as one term appearing twice.
        weights: dict[int, float] = {}
        for term, count in counts.items():
            weights[term_index(term)] = weights.get(term_index(term), 0.0) + math.log1p(count)

        # Sorted so the same text always produces the same vector byte-for-byte,
        # which makes an ingestion diffable and a test assertable.
        items = sorted(weights.items())
        return SparseText(
            indices=[index for index, _ in items],
            values=[round(value, 6) for _, value in items],
        )

    def encode_query(self, text: str) -> SparseText:
        """A query is encoded exactly as a passage is.

        Deliberately the same function. Two different encoders for the two sides
        of the same comparison is the classic way to build an index nothing can
        find anything in.
        """
        return self.encode(text)
