"""How the worker turns a ``file_reference`` into bytes.

Django owns document storage. This service must not import Django's storage
layer, and — more importantly — must not assume that because Django's container
can see `/uploads`, this one can. Two containers with the same path is a
coincidence of a compose file, not a property of the system, and a worker that
quietly reads a stale or empty directory produces an index of nothing while
reporting success.

So the resolution is explicit and has two implementations:

``HttpFileResolver``   asks the backend for the bytes over an authenticated
                       internal route. Assumes nothing about where the worker
                       runs, works across hosts, and is the default.

``LocalFileResolver``  reads a directory that really is the same volume Django
                       writes to. Faster and one less moving part, but only
                       correct when the deployment actually mounts it, which is
                       why it must be turned on deliberately.

Both refuse a reference that escapes their root, and both are handed a key
rather than a path — the storage layout is Django's business.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

import httpx

from app.core.errors import ContentHashMismatch, DocumentNotFound, InvalidConfiguration
from app.core.logging import get_logger

logger = get_logger(__name__)

# Hashed in blocks rather than whole: a 25 MB PDF should not also cost 25 MB of
# resident memory in a worker that is already holding two ML models.
_HASH_BLOCK = 1024 * 1024


def sha256_of(data: bytes) -> str:
    digest = hashlib.sha256()
    for start in range(0, len(data), _HASH_BLOCK):
        digest.update(data[start : start + _HASH_BLOCK])
    return digest.hexdigest()


def _safe_key(reference: str) -> PurePosixPath:
    """Validate a storage key, or refuse it.

    The schema already rejects traversal at the edge; this repeats the check at
    the point of use, because that is where being wrong actually opens a file.
    """
    cleaned = reference.strip().replace("\\", "/")
    candidate = PurePosixPath(cleaned)
    if candidate.is_absolute() or ".." in candidate.parts or not cleaned:
        raise DocumentNotFound(f"unsafe file reference: {reference!r}")
    return candidate


class FileResolver(ABC):
    """Turns a storage key into bytes."""

    @abstractmethod
    async def fetch(self, reference: str) -> bytes: ...

    async def fetch_verified(self, reference: str, expected_hash: str) -> bytes:
        """Fetch, and refuse to hand back content the record does not describe.

        A DocumentVersion's bytes are immutable by design, so a hash that has
        moved means storage no longer holds what the version was created from.
        Indexing it anyway would produce a corpus that cites a document nobody
        can verify, and the mismatch would be invisible from either side.
        """
        data = await self.fetch(reference)
        actual = sha256_of(data)
        if expected_hash and actual != expected_hash:
            raise ContentHashMismatch(
                f"stored content does not match the version record "
                f"(expected {expected_hash[:12]}…, found {actual[:12]}…)"
            )
        return data

    async def close(self) -> None:  # pragma: no cover - optional override
        return None


class LocalFileResolver(FileResolver):
    """Reads a directory shared with the backend.

    Only correct when the deployment mounts Django's MEDIA_ROOT here; see the
    volume note in docker/docker-compose.yml.
    """

    def __init__(self, root: str) -> None:
        if not root:
            raise InvalidConfiguration("DOCUMENT_STORAGE_ROOT is required for local storage")
        self._root = Path(root).resolve()

    async def fetch(self, reference: str) -> bytes:
        target = (self._root / _safe_key(reference)).resolve()

        # Belt and braces after resolve(): a symlink inside the root could still
        # point outside it, and resolve() would have followed it.
        if not target.is_relative_to(self._root):
            raise DocumentNotFound(f"file reference escapes the storage root: {reference!r}")
        if not target.is_file():
            raise DocumentNotFound(
                f"{reference!r} is not in storage at {self._root}. If the worker and the "
                "backend do not share this volume, use DOCUMENT_STORAGE=http."
            )

        return target.read_bytes()


class HttpFileResolver(FileResolver):
    """Asks the backend for the file over its internal route.

    The token goes in a header, never in the URL: a URL reaches access logs,
    proxies and error reports, and a secret that has been in one of those is no
    longer a secret.
    """

    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        if not base_url:
            raise InvalidConfiguration("BACKEND_URL is required for http document storage")
        if not token:
            raise InvalidConfiguration("AI_SERVICE_INTERNAL_TOKEN is required")
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def fetch(self, reference: str) -> bytes:
        _safe_key(reference)  # refuse before it reaches the wire
        url = f"{self._base}/api/internal/knowledge/documents/file/"

        try:
            response = await self._http().get(
                url,
                params={"reference": reference},
                headers={"X-Internal-Token": self._token},
            )
        except httpx.HTTPError as exc:
            # Network trouble reaching the backend is not "the document is
            # missing" — it is a transient the task should retry, so it is
            # raised as one rather than as DocumentNotFound.
            from app.core.errors import IngestionError

            error = IngestionError(f"could not reach the backend for {reference!r}: {exc}")
            error.retryable = True
            raise error from exc

        if response.status_code == 404:
            raise DocumentNotFound(f"the backend has no file at {reference!r}")
        if response.status_code in (401, 403):
            raise InvalidConfiguration(
                "the backend rejected AI_SERVICE_INTERNAL_TOKEN when fetching a document"
            )
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def build_resolver(settings) -> FileResolver:
    """The resolver this deployment is configured for."""
    if settings.document_storage == "local":
        return LocalFileResolver(settings.document_storage_root or "")
    return HttpFileResolver(
        base_url=settings.backend_url or "",
        token=settings.ai_service_internal_token or "",
        timeout=settings.backend_timeout,
    )
