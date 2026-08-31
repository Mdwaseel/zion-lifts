"""The ingestion workflow, against fakes.

These are the tests that hold the phase's central promises: a partial index is
never searchable, a retry does not duplicate anything, and the edition currently
answering questions survives a failed replacement.
"""

from __future__ import annotations

import hashlib

import pytest

from app.api.schemas.document import IngestionRequest
from app.core.constants import DocumentStatus, JobOperation
from app.core.errors import (
    ContentHashMismatch,
    DocumentNotFound,
    EmbeddingDimensionMismatch,
    EmbeddingFailed,
    InvalidDocument,
    VectorStoreUnavailable,
)
from app.ingestion.pipeline import IngestionPipeline, point_id
from app.ingestion.processors.chunker import RecursiveChunker
from app.vectorstore.collections import CollectionNameBuilder
from tests.conftest import FakeEmbeddings, InMemoryVectorStore
from tests.conftest_worker import FakeResolver, FlakyStore, RecordingReporter, active_points

KB = "kb-7"
DOCUMENT = "doc-1"
VERSION_1 = "ver-1"
VERSION_2 = "ver-2"
JOB = "job-1"

# Long enough to chunk into several pieces at the size used below.
BODY = (
    "Zion machine-room-less lifts place the gearless machine in the headroom. "
    "Shaft width is 1600 mm and depth 1750 mm for a six person car. "
    "The pit is 1200 mm deep and headroom is 3600 mm. "
    "Installation runs twelve to sixteen working days once the shaft is ready. "
) * 6


def pdf_bytes(body: str = BODY) -> bytes:
    """A byte string the fake resolver hands over; the loader is stubbed."""
    return body.encode("utf-8")


class StubPdfLoader:
    """Stands in for pypdf: turns bytes back into text with a page marker."""

    def __init__(
        self, pages: int = 3, fail: Exception | None = None, text: str | None = None
    ) -> None:
        self._pages = pages
        self._fail = fail
        # `text=""` stands in for a scanned PDF: pypdf reads it fine and finds
        # no text layer at all.
        self._text = text

    async def load_bytes(self, data: bytes, filename: str):
        if self._fail:
            raise self._fail
        from app.ingestion.loaders.text_loader import LoadedDocument

        body = self._text if self._text is not None else data.decode("utf-8")
        return LoadedDocument(
            text=f"\n\n[[page:1]]\n\n{body}" if body else "",
            source=filename,
            source_type="pdf",
            metadata={"filename": filename, "pages": self._pages},
        )


def build(
    *,
    store: object | None = None,
    resolver: FakeResolver | None = None,
    reporter: RecordingReporter | None = None,
    embeddings: FakeEmbeddings | None = None,
    loader: StubPdfLoader | None = None,
) -> tuple[IngestionPipeline, InMemoryVectorStore, RecordingReporter]:
    store = store or InMemoryVectorStore()
    reporter = reporter or RecordingReporter()
    embeddings = embeddings or FakeEmbeddings()
    pipeline = IngestionPipeline(
        embeddings=embeddings,
        store=store,  # type: ignore[arg-type]
        chunker=RecursiveChunker(200, 20),
        resolver=resolver or FakeResolver({"knowledge/doc-1/v1.pdf": pdf_bytes()}),
        reporter=reporter,  # type: ignore[arg-type]
        embedding_model_version="v1",
    )
    pipeline._pdf = loader or StubPdfLoader()  # type: ignore[assignment]
    return pipeline, store, reporter


def request_for(
    version: str = VERSION_1,
    *,
    reference: str = "knowledge/doc-1/v1.pdf",
    content_hash: str = "",
    operation: JobOperation = JobOperation.INGEST,
) -> IngestionRequest:
    return IngestionRequest(
        job_id=JOB,
        document_id=DOCUMENT,
        document_version_id=version,
        knowledge_base_id=KB,
        file_reference=reference,
        content_hash=content_hash,
        operation=operation,
    )


class TestHappyPath:
    async def test_a_document_is_extracted_chunked_embedded_and_indexed(self):
        pipeline, store, reporter = build()
        outcome = await pipeline.ingest(request_for())

        assert outcome.chunk_count > 1
        assert outcome.page_count == 3
        assert outcome.collection == CollectionNameBuilder.build(KB, "fake", "v1", 8)
        assert len(store.collections[outcome.collection]) == outcome.chunk_count

    async def test_every_stage_is_reported_in_order(self):
        pipeline, _, reporter = build()
        await pipeline.ingest(request_for())

        assert reporter.stages == [
            DocumentStatus.PROCESSING,
            DocumentStatus.EXTRACTING,
            DocumentStatus.CHUNKING,
            DocumentStatus.EMBEDDING,
            DocumentStatus.INDEXING,
            DocumentStatus.READY,
        ]

    async def test_ready_is_reported_last_and_carries_the_measurements(self):
        pipeline, _, reporter = build()
        outcome = await pipeline.ingest(request_for())

        final = reporter.last()
        assert final["stage"] == DocumentStatus.READY
        assert final["progress"] == 100
        assert final["page_count"] == 3
        assert final["chunk_count"] == outcome.chunk_count
        assert final["embedding_dimension"] == 8
        assert final["collection"] == outcome.collection

    async def test_counts_are_measured_not_echoed(self):
        # The request carries no counts at all; everything reported was observed.
        pipeline, _, reporter = build()
        await pipeline.ingest(request_for())
        assert reporter.last()["chunk_count"] > 0

    async def test_reports_never_contain_document_text(self):
        pipeline, _, reporter = build()
        await pipeline.ingest(request_for())
        for report in reporter.reports:
            assert "Zion machine-room-less" not in str(report)


class TestChunkPayload:
    async def test_every_chunk_carries_its_ownership_and_version(self):
        pipeline, store, _ = build()
        outcome = await pipeline.ingest(request_for())

        for record in store.collections[outcome.collection].values():
            assert record.metadata["knowledge_base_id"] == KB
            assert record.metadata["document_version_id"] == VERSION_1
            assert record.document_id == DOCUMENT
            assert "chunk_id" in record.metadata
            assert "content_hash" in record.metadata

    async def test_page_numbers_survive_into_the_payload(self):
        pipeline, store, _ = build()
        outcome = await pipeline.ingest(request_for())
        pages = {r.metadata.get("page") for r in store.collections[outcome.collection].values()}
        assert pages == {1}

    async def test_the_collection_is_named_for_the_embedding_actually_used(self):
        pipeline, _, _ = build()
        outcome = await pipeline.ingest(request_for())
        # "fake" is FakeEmbeddings.model_name — the provider that answered, not
        # whatever the request happened to say.
        assert "fake" in outcome.collection
        assert outcome.collection.startswith("kb_kb_7__")

    async def test_the_collection_name_carries_the_vector_width(self):
        # The last guard against two geometries in one index: a model revision
        # that changed width gets a different collection rather than colliding
        # with its own past.
        pipeline, _, _ = build()
        outcome = await pipeline.ingest(request_for())
        assert outcome.collection.endswith("_d8")


class TestVisibility:
    async def test_chunks_are_active_once_the_run_completes(self):
        pipeline, store, _ = build()
        outcome = await pipeline.ingest(request_for())
        assert len(active_points(store, outcome.collection)) == outcome.chunk_count

    async def test_a_run_that_dies_during_indexing_leaves_nothing_searchable(self):
        # The central promise: 700 of 1000 chunks written is 0 chunks answering.
        store = InMemoryVectorStore()
        flaky = FlakyStore(store, "set_flag", times=1, error=VectorStoreUnavailable("boom"))
        pipeline, _, _ = build(store=flaky)

        with pytest.raises(VectorStoreUnavailable):
            await pipeline.ingest(request_for())

        collection = CollectionNameBuilder.build(KB, "fake", "v1", 8)
        assert store.collections[collection]  # points were written
        assert active_points(store, collection) == []  # and none of them is visible

    async def test_a_failed_second_version_leaves_the_first_answering(self):
        store = InMemoryVectorStore()
        pipeline, _, _ = build(store=store)
        first = await pipeline.ingest(request_for(VERSION_1))
        assert len(active_points(store, first.collection)) == first.chunk_count

        # Version 2 gets as far as writing points, then fails before activation.
        flaky = FlakyStore(store, "set_flag", times=1, error=VectorStoreUnavailable("boom"))
        second_pipeline, _, _ = build(
            store=flaky,
            resolver=FakeResolver({"knowledge/doc-1/v2.pdf": pdf_bytes(BODY + " Revised.")}),
        )
        with pytest.raises(VectorStoreUnavailable):
            await second_pipeline.ingest(request_for(VERSION_2, reference="knowledge/doc-1/v2.pdf"))

        # Every visible chunk still belongs to version 1.
        visible = active_points(store, first.collection)
        assert len(visible) == first.chunk_count
        assert {r.metadata["document_version_id"] for r in visible} == {VERSION_1}

    async def test_a_successful_second_version_replaces_the_first(self):
        store = InMemoryVectorStore()
        pipeline, _, _ = build(store=store)
        await pipeline.ingest(request_for(VERSION_1))

        second_pipeline, _, _ = build(
            store=store,
            resolver=FakeResolver({"knowledge/doc-1/v2.pdf": pdf_bytes(BODY + " Revised.")}),
        )
        second = await second_pipeline.ingest(
            request_for(VERSION_2, reference="knowledge/doc-1/v2.pdf")
        )

        visible = active_points(store, second.collection)
        assert {r.metadata["document_version_id"] for r in visible} == {VERSION_2}
        # The superseded edition is gone rather than lingering as dead weight.
        everything = store.collections[second.collection]
        assert all(r.metadata["document_version_id"] == VERSION_2 for r in everything.values())


class TestIdempotency:
    async def test_point_ids_are_deterministic(self):
        assert point_id(VERSION_1, 0) == point_id(VERSION_1, 0)
        assert point_id(VERSION_1, 0) != point_id(VERSION_1, 1)
        assert point_id(VERSION_1, 0) != point_id(VERSION_2, 0)

    async def test_running_the_same_ingestion_twice_changes_nothing(self):
        store = InMemoryVectorStore()
        pipeline, _, _ = build(store=store)

        first = await pipeline.ingest(request_for())
        ids_after_first = set(store.collections[first.collection])

        second = await pipeline.ingest(request_for())
        ids_after_second = set(store.collections[second.collection])

        assert first.chunk_count == second.chunk_count
        assert ids_after_first == ids_after_second
        assert len(active_points(store, first.collection)) == first.chunk_count

    async def test_a_retry_after_a_partial_write_converges(self):
        store = InMemoryVectorStore()
        flaky = FlakyStore(store, "set_flag", times=1, error=VectorStoreUnavailable("boom"))
        broken, _, _ = build(store=flaky)
        with pytest.raises(VectorStoreUnavailable):
            await broken.ingest(request_for())

        # The retry is a whole fresh run against the same version.
        pipeline, _, _ = build(store=store)
        outcome = await pipeline.ingest(request_for())
        assert len(store.collections[outcome.collection]) == outcome.chunk_count
        assert len(active_points(store, outcome.collection)) == outcome.chunk_count


class TestDeletion:
    async def test_deleting_removes_only_that_document(self):
        store = InMemoryVectorStore()
        pipeline, _, _ = build(store=store)
        outcome = await pipeline.ingest(request_for())

        other = IngestionRequest(
            job_id=JOB,
            document_id="doc-2",
            document_version_id="ver-9",
            knowledge_base_id=KB,
            file_reference="knowledge/doc-2/v1.pdf",
        )
        other_pipeline, _, _ = build(
            store=store,
            resolver=FakeResolver({"knowledge/doc-2/v1.pdf": pdf_bytes("Another document. " * 30)}),
        )
        await other_pipeline.ingest(other)

        removed = await pipeline.delete(request_for(operation=JobOperation.DELETE))
        assert removed == outcome.chunk_count

        remaining = store.collections[outcome.collection]
        assert remaining
        assert all(r.document_id == "doc-2" for r in remaining.values())

    async def test_deleting_twice_is_not_a_failure(self):
        store = InMemoryVectorStore()
        pipeline, _, reporter = build(store=store)
        await pipeline.ingest(request_for())

        assert await pipeline.delete(request_for(operation=JobOperation.DELETE)) > 0
        # A redelivered message finds the work already done.
        assert await pipeline.delete(request_for(operation=JobOperation.DELETE)) == 0
        assert reporter.stages[-1] == DocumentStatus.DELETED

    async def test_deleting_something_never_indexed_is_not_a_failure(self):
        pipeline, _, _ = build()
        assert await pipeline.delete(request_for(operation=JobOperation.DELETE)) == 0


class TestFailures:
    async def test_a_missing_file_is_permanent(self):
        pipeline, _, _ = build(resolver=FakeResolver({}))
        with pytest.raises(DocumentNotFound) as caught:
            await pipeline.ingest(request_for())
        assert not caught.value.retryable

    async def test_a_hash_that_does_not_match_is_permanent(self):
        pipeline, _, _ = build()
        with pytest.raises(ContentHashMismatch) as caught:
            await pipeline.ingest(request_for(content_hash="0" * 64))
        assert not caught.value.retryable

    async def test_a_matching_hash_is_accepted(self):
        data = pdf_bytes()
        pipeline, _, _ = build(resolver=FakeResolver({"knowledge/doc-1/v1.pdf": data}))
        outcome = await pipeline.ingest(request_for(content_hash=hashlib.sha256(data).hexdigest()))
        assert outcome.chunk_count > 0

    async def test_a_pdf_with_no_text_is_permanent(self):
        # A scan with no text layer. The same bytes produce the same nothing on
        # every retry, so retrying is only a slower way to fail.
        pipeline, _, _ = build(loader=StubPdfLoader(pages=1, text=""))
        with pytest.raises(InvalidDocument) as caught:
            await pipeline.ingest(
                request_for(reference="knowledge/doc-1/v1.pdf"),
            )
        assert not caught.value.retryable

    async def test_an_unreadable_pdf_is_permanent(self):
        pipeline, _, _ = build(loader=StubPdfLoader(fail=ValueError("not a pdf")))
        from app.core.errors import PdfExtractionFailed

        with pytest.raises(PdfExtractionFailed) as caught:
            await pipeline.ingest(request_for())
        assert not caught.value.retryable

    async def test_an_embedding_failure_is_retryable(self):
        class BrokenEmbeddings(FakeEmbeddings):
            async def embed_documents(self, texts):
                raise RuntimeError("provider rate limited")

        pipeline, _, _ = build(embeddings=BrokenEmbeddings())
        with pytest.raises(EmbeddingFailed) as caught:
            await pipeline.ingest(request_for())
        assert caught.value.retryable

    async def test_qdrant_being_unavailable_is_retryable(self):
        store = InMemoryVectorStore()
        flaky = FlakyStore(store, "upsert", times=1, error=VectorStoreUnavailable("down"))
        pipeline, _, _ = build(store=flaky)

        with pytest.raises(VectorStoreUnavailable) as caught:
            await pipeline.ingest(request_for())
        assert caught.value.retryable

    async def test_a_dimension_mismatch_is_permanent_and_writes_nothing(self):
        # Padding or truncating a vector produces a number that is not a
        # distance, so this must never be worked around.
        store = InMemoryVectorStore()
        collection = CollectionNameBuilder.build(KB, "fake", "v1", 8)
        await store.ensure_collection(collection, 768)  # built for another model

        pipeline, _, _ = build(store=store)
        with pytest.raises(EmbeddingDimensionMismatch) as caught:
            await pipeline.ingest(request_for())

        assert not caught.value.retryable
        assert store.collections[collection] == {}

    async def test_a_failure_report_names_a_stable_error_code(self):
        pipeline, _, reporter = build(resolver=FakeResolver({}))
        from app.core.errors import classify

        try:
            await pipeline.ingest(request_for())
        except Exception as exc:
            await pipeline.report_failure(request_for(), classify(exc))

        final = reporter.last()
        assert final["stage"] == DocumentStatus.FAILED
        assert final["error_code"] == "DOCUMENT_NOT_FOUND"

    async def test_a_callback_failure_stops_the_run(self):
        # A run whose result never reached Django is a run whose result does not
        # exist, so it must not be reported as a success.
        from app.core.errors import CallbackFailed

        pipeline, _, _ = build(reporter=RecordingReporter(fail_on=DocumentStatus.READY))
        with pytest.raises(CallbackFailed):
            await pipeline.ingest(request_for())
