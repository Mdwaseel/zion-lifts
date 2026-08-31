"""BM25 lexical search over the chunks fetched from the store.

Dense retrieval misses exact identifiers, error codes and rare proper nouns.
BM25 catches those, and hybrid_search fuses the two rankings.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.vectorstore.base import ScoredChunk, VectorStore

_TOKEN = re.compile(r"[a-z0-9_]+")
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have how in is it its of on or that "
    "the then there these this to was were what when where which who why will "
    "with".split()
)

K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


@dataclass(slots=True)
class BM25Index:
    docs: list[list[str]]
    doc_freq: Counter[str]
    avg_len: float

    @classmethod
    def build(cls, texts: list[str]) -> BM25Index:
        docs = [tokenize(t) for t in texts]
        doc_freq: Counter[str] = Counter()
        for tokens in docs:
            doc_freq.update(set(tokens))
        avg_len = (sum(len(d) for d in docs) / len(docs)) if docs else 0.0
        return cls(docs=docs, doc_freq=doc_freq, avg_len=avg_len)

    def score(self, query_tokens: list[str]) -> list[float]:
        n = len(self.docs)
        if not n or not self.avg_len:
            return [0.0] * n

        scores = [0.0] * n
        for i, tokens in enumerate(self.docs):
            if not tokens:
                continue
            counts = Counter(tokens)
            length = len(tokens)
            total = 0.0
            for term in query_tokens:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                norm = tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / self.avg_len))
                total += idf * norm
            scores[i] = total
        return scores


class KeywordSearch:
    """Scans a bounded slice of the collection and ranks it with BM25.

    `scan_limit` caps how much is pulled into memory; for corpora larger than
    that, swap this for a server-side sparse index.
    """

    def __init__(self, store: VectorStore, scan_limit: int = 2000) -> None:
        self._store = store
        self._scan_limit = scan_limit

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        page_size = min(self._scan_limit, 500)
        chunks, offset = await self._store.scroll(collection, filters, limit=page_size)
        while offset and len(chunks) < self._scan_limit:
            more, offset = await self._store.scroll(
                collection, filters, limit=min(self._scan_limit - len(chunks), 500), offset=offset
            )
            if not more:
                break
            chunks.extend(more)

        if not chunks:
            return []

        index = BM25Index.build([c.text for c in chunks])
        scores = index.score(query_tokens)

        ranked = sorted(
            (
                ScoredChunk(
                    id=chunk.id,
                    text=chunk.text,
                    document_id=chunk.document_id,
                    score=score,
                    metadata=chunk.metadata,
                )
                for chunk, score in zip(chunks, scores, strict=True)
                if score > 0
            ),
            key=lambda c: c.score,
            reverse=True,
        )
        return ranked[:top_k]
