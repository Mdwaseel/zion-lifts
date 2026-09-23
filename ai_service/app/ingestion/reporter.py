"""Telling the backend what happened.

The worker holds no database. Everything it learns about a document — which
stage it reached, how many pages it had, why it failed — reaches Django through
this one client, over the internal route, and nowhere else. That is the whole
reason the boundary holds: there is no second path by which a worker could
change a business record.

A report that never lands is treated as a failure of the run, not as a detail.
A version that was indexed but never reported is a version Django still believes
is processing, and the vectors it wrote are invisible for ever.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.core.errors import CallbackFailed
from app.core.logging import get_logger

logger = get_logger(__name__)

CALLBACK_PATH = "/api/internal/knowledge/ingestion-report/"

# Worth trying again: the backend is restarting, a proxy hiccupped, the request
# timed out. Anything else — 400, 404, 409 — means the backend understood us and
# said no, and repeating the same message will get the same answer.
_RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class StageReporter:
    """Posts ingestion reports, with a short in-process retry.

    The retry here is deliberately small and separate from Celery's. A one
    second blip should cost one second, not a re-run of the embedding pass that
    produced the numbers being reported.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 15.0,
        retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}{CALLBACK_PATH}"
        self._token = token
        self._timeout = timeout
        self._retries = retries
        self._client = client
        self._owns_client = client is None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def send(self, report: dict[str, Any]) -> None:
        """Deliver one report, or raise CallbackFailed.

        Every field of ``report`` is an identifier, a stage, a count or an error
        code. Document text never appears in one, and neither does the token,
        which travels as a header.
        """
        last: str = "not attempted"

        for attempt in range(1, self._retries + 1):
            started = time.perf_counter()
            try:
                response = await self._http().post(
                    self._url,
                    json=report,
                    headers={"X-Internal-Token": self._token},
                )
            except httpx.HTTPError as exc:
                last = f"{type(exc).__name__}: {exc}"
            else:
                took_ms = (time.perf_counter() - started) * 1000
                if response.is_success:
                    logger.debug(
                        "ingestion report delivered",
                        extra={
                            "stage": report.get("stage"),
                            "status": response.status_code,
                            "took_ms": round(took_ms, 1),
                        },
                    )
                    return

                last = f"HTTP {response.status_code}: {response.text[:300]}"
                if response.status_code not in _RETRY_STATUS:
                    # The backend understood and refused. Saying it again will
                    # not change the answer, so fail now rather than after three
                    # more identical rejections.
                    raise CallbackFailed(f"backend rejected the report — {last}")

            if attempt < self._retries:
                # Short, linear, and bounded: this is a blip, not an outage. A
                # real outage is Celery's problem, and it backs off properly.
                await asyncio.sleep(min(2**attempt, 8))

        raise CallbackFailed(
            f"could not report to the backend after {self._retries} attempts — {last}"
        )

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None
