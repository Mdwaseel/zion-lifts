"""Holds the current website index and decides when to rebuild it.

A chat request must never wait on the content API. The site's copy changes when
somebody publishes a lift — minutes or days apart — while questions arrive
continuously, so the index is refreshed on a timer *beside* the request path and
every request reads whatever the last successful build produced.

That gives the three properties that matter:

*Reads never block.* :meth:`WebsiteIndexProvider.current` is an attribute read.
There is no lock on the fast path, because a rebuild swaps a whole new immutable
index into place rather than mutating the one being read.

*A failed refresh keeps the previous answer.* A backend that is down leaves the
last good index serving. Only the very first build can produce the static-only
index, and that is still a correct one — it just cannot name products.

*Only one rebuild runs at a time.* Several requests noticing a stale index
together must not start several fetches of the same content.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from app.core.logging import get_logger
from app.core.metrics import metrics
from app.website.builder import build_index, build_pages
from app.website.index import WebsiteIndex

logger = get_logger(__name__)


class WebsiteIndexProvider:
    """The service's single source for "what pages exist and what do they say".

    Construction is cheap and synchronous — it installs the static index — so
    the object is usable the instant the container exists. :meth:`start` then
    does the first real build; failing it is not fatal.
    """

    __slots__ = ("_index", "_base_url", "_client", "_ttl", "_timeout", "_lock", "_refreshing")

    def __init__(
        self,
        base_url: str | None,
        ttl_seconds: float = 900.0,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._ttl = ttl_seconds
        self._timeout = timeout
        self._client = client
        self._lock = asyncio.Lock()
        self._refreshing = False
        # Static from the first instant: an assistant that cannot yet name a
        # product should still be able to link to the products page.
        self._index = WebsiteIndex(build_pages(None), generated_at=0.0)

    @property
    def current(self) -> WebsiteIndex:
        """The index to answer with. Never None, never mid-update."""
        return self._index

    @property
    def is_stale(self) -> bool:
        return (time.time() - self._index.generated_at) > self._ttl

    async def start(self) -> None:
        """Build once at start-up. Logged and swallowed on failure."""
        await self.refresh()

    async def refresh(self) -> WebsiteIndex:
        """Rebuild now, or return the current index if a rebuild is in flight."""
        if self._refreshing:
            return self._index
        async with self._lock:
            if self._refreshing:  # pragma: no cover - lost the race, nothing to do
                return self._index
            self._refreshing = True
            started = time.perf_counter()
            try:
                index = await build_index(self._base_url, self._client, self._timeout)
            except Exception as exc:
                metrics.increment("website_index_refresh_total", status="error")
                logger.warning(
                    "website index refresh failed; keeping the previous index",
                    extra={"error_type": type(exc).__name__, "pages": len(self._index)},
                )
                return self._index
            finally:
                self._refreshing = False

            took_ms = (time.perf_counter() - started) * 1000
            metrics.increment("website_index_refresh_total", status="ok")
            metrics.observe("website_index_build_duration", took_ms)
            metrics.set_gauge("website_index_pages", float(len(index)))
            self._index = index
            return index

    async def refresh_if_stale(self) -> None:
        """Rebuild only when the TTL has passed. Safe to call per request."""
        if self.is_stale and not self._refreshing:
            await self.refresh()


__all__ = ["WebsiteIndexProvider"]
