"""The storage boundary: what the worker will and will not read."""

from __future__ import annotations

import hashlib

import pytest

from app.core.config import Settings
from app.core.errors import ContentHashMismatch, DocumentNotFound, InvalidConfiguration
from app.ingestion.files import (
    HttpFileResolver,
    LocalFileResolver,
    build_resolver,
    sha256_of,
)

BARE = {"_env_file": None}
BODY = b"%PDF-1.4\nbody\n"


@pytest.fixture
def storage(tmp_path):
    root = tmp_path / "uploads"
    (root / "knowledge" / "doc-1").mkdir(parents=True)
    (root / "knowledge" / "doc-1" / "v1.pdf").write_bytes(BODY)
    # Something that exists outside the root, to try to reach.
    (tmp_path / "secret.env").write_bytes(b"DJANGO_SECRET_KEY=hunter2")
    return root


class TestLocalResolver:
    async def test_a_stored_file_is_returned(self, storage):
        resolver = LocalFileResolver(str(storage))
        assert await resolver.fetch("knowledge/doc-1/v1.pdf") == BODY

    async def test_a_missing_file_is_reported_as_missing(self, storage):
        resolver = LocalFileResolver(str(storage))
        with pytest.raises(DocumentNotFound):
            await resolver.fetch("knowledge/doc-1/v9.pdf")

    async def test_the_error_names_the_http_alternative(self, storage):
        # The commonest cause is the two containers not actually sharing the
        # volume, so the message says what to do about it.
        resolver = LocalFileResolver(str(storage))
        with pytest.raises(DocumentNotFound) as caught:
            await resolver.fetch("knowledge/doc-1/v9.pdf")
        assert "DOCUMENT_STORAGE=http" in str(caught.value)

    @pytest.mark.parametrize(
        "reference",
        [
            "../secret.env",
            "../../secret.env",
            "knowledge/../../secret.env",
            "/etc/passwd",
            "\\windows\\system32",
            "..\\..\\secret.env",
        ],
    )
    async def test_a_reference_that_escapes_the_root_is_refused(self, storage, reference):
        resolver = LocalFileResolver(str(storage))
        with pytest.raises(DocumentNotFound):
            await resolver.fetch(reference)

    async def test_an_empty_reference_is_refused(self, storage):
        resolver = LocalFileResolver(str(storage))
        with pytest.raises(DocumentNotFound):
            await resolver.fetch("")

    def test_a_resolver_without_a_root_will_not_be_built(self):
        with pytest.raises(InvalidConfiguration):
            LocalFileResolver("")


class TestHashVerification:
    async def test_content_matching_the_record_is_accepted(self, storage):
        resolver = LocalFileResolver(str(storage))
        digest = hashlib.sha256(BODY).hexdigest()
        assert await resolver.fetch_verified("knowledge/doc-1/v1.pdf", digest) == BODY

    async def test_content_that_has_changed_underneath_is_refused(self, storage):
        # A version's bytes are immutable by design, so a moved hash means
        # storage no longer holds what the record describes. Indexing it would
        # produce a corpus citing a document nobody can verify.
        resolver = LocalFileResolver(str(storage))
        with pytest.raises(ContentHashMismatch):
            await resolver.fetch_verified("knowledge/doc-1/v1.pdf", "0" * 64)

    async def test_an_absent_expected_hash_skips_the_check(self, storage):
        resolver = LocalFileResolver(str(storage))
        assert await resolver.fetch_verified("knowledge/doc-1/v1.pdf", "") == BODY

    def test_the_hash_matches_hashlib(self):
        assert sha256_of(BODY) == hashlib.sha256(BODY).hexdigest()


class TestResolverSelection:
    def test_http_is_the_default(self):
        # It assumes nothing about where the worker runs, which is the safe
        # default when the alternative fails silently.
        assert Settings(**BARE).document_storage == "http"

    def test_the_configured_resolver_is_built(self, tmp_path):
        http = build_resolver(
            Settings(
                **BARE,
                backend_url="http://backend:8000",
                ai_service_internal_token="t" * 40,
            )
        )
        assert isinstance(http, HttpFileResolver)

        local = build_resolver(
            Settings(**BARE, document_storage="local", document_storage_root=str(tmp_path))
        )
        assert isinstance(local, LocalFileResolver)

    def test_an_http_resolver_needs_a_backend_and_a_token(self):
        with pytest.raises(InvalidConfiguration):
            HttpFileResolver(base_url="", token="t")
        with pytest.raises(InvalidConfiguration):
            HttpFileResolver(base_url="http://backend", token="")

    def test_local_storage_without_a_root_is_refused_at_configuration_time(self):
        from app.core.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            Settings(
                **BARE,
                environment="production",
                document_storage="local",
                document_storage_root=None,
                qdrant_url="https://c.qdrant.io",
                qdrant_api_key="k",
                redis_url="redis://cache:6379/0",
                api_keys="k",
                internal_token="i" * 40,
                cors_origins="https://zionlifts.com",
                gemini_api_key="g",
                backend_url="http://backend:8000",
                ai_service_internal_token="t" * 40,
            )
