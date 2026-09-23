"""Doubles for the ingestion worker's dependencies.

Kept apart from ``tests/conftest.py`` so the retrieval fixtures there stay
about retrieval. Everything here stands in for something the worker talks to
over a socket: a storage backend, a Django callback, and Qdrant.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import DocumentNotFound
from app.ingestion.files import FileResolver
from app.vectorstore.collections import ACTIVE_FIELD


class FakeResolver(FileResolver):
    """Storage as a dict. Verifies hashes exactly as the real one does, because
    that check is the thing several tests are about."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.files = files or {}

    async def fetch(self, reference: str) -> bytes:
        try:
            return self.files[reference]
        except KeyError:
            raise DocumentNotFound(f"no such file: {reference}") from None


class RecordingReporter:
    """Captures reports instead of posting them.

    Every test that asserts on ordering — PROCESSING before EXTRACTING, READY
    last — reads ``self.reports``.
    """

    def __init__(self, fail_on: str | None = None) -> None:
        self.reports: list[dict[str, Any]] = []
        self._fail_on = fail_on

    async def send(self, report: dict[str, Any]) -> None:
        if self._fail_on and report.get("stage") == self._fail_on:
            from app.core.errors import CallbackFailed

            raise CallbackFailed(f"refusing to accept a {self._fail_on} report")
        self.reports.append(report)

    async def close(self) -> None:
        return None

    @property
    def stages(self) -> list[str]:
        return [r["stage"] for r in self.reports]

    def last(self) -> dict[str, Any]:
        return self.reports[-1]


class FlakyStore:
    """Wraps a store and fails a named method a set number of times.

    Used to prove that a transient Qdrant failure is retried and a permanent
    one is not, without needing a Qdrant to break.
    """

    def __init__(self, inner: Any, method: str, times: int, error: Exception) -> None:
        self._inner = inner
        self._method = method
        self._remaining = times
        self._error = error

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._inner, name)
        if name != self._method:
            return attr

        async def guarded(*args: Any, **kwargs: Any) -> Any:
            if self._remaining > 0:
                self._remaining -= 1
                raise self._error
            return await attr(*args, **kwargs)

        return guarded


def active_points(store: Any, collection: str) -> list[Any]:
    """Points a search would actually see. Mirrors the retrieval filter."""
    return [
        record
        for record in store.collections.get(collection, {}).values()
        if record.metadata.get(ACTIVE_FIELD) is True
    ]
