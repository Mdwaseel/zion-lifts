"""In-process LRU cache for embeddings, keyed by model + text hash."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from threading import Lock


def cache_key(model: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{model}:{digest}"


class EmbeddingCache:
    """Bounded, thread-safe LRU. Embedding the same text twice is common in
    evaluation runs and repeated queries, and encoding is the expensive part."""

    def __init__(self, max_size: int = 4096) -> None:
        self._max_size = max(0, max_size)
        self._store: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> list[float] | None:
        if not self._max_size:
            return None
        with self._lock:
            vector = self._store.get(key)
            if vector is None:
                self.misses += 1
                return None
            self._store.move_to_end(key)
            self.hits += 1
            return vector

    def set(self, key: str, vector: list[float]) -> None:
        if not self._max_size:
            return
        with self._lock:
            self._store[key] = vector
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = self.misses = 0

    def stats(self) -> dict[str, int | float]:
        total = self.hits + self.misses
        return {
            "size": len(self._store),
            "max_size": self._max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }
