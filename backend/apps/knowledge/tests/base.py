"""Fixtures for the knowledge tests.

Every test here runs with ingestion queuing disabled unless it is specifically
testing the handover. There is no broker in the test environment, and a test
that silently depends on one is a test that passes on this machine only.
"""

from __future__ import annotations

import io
import logging
from contextlib import contextmanager
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.knowledge.models import KnowledgeBase

User = get_user_model()

# The smallest thing that is genuinely a PDF: the signature, one object, and a
# trailer. Real enough to pass the signature check, small enough to read.
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
    b"trailer<</Root 1 0 R>>\n"
    b"%%EOF\n"
)


def pdf_upload(name: str = "policy.pdf", body: bytes = MINIMAL_PDF) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, body, content_type="application/pdf")


def raw_upload(name: str, body: bytes, content_type: str = "application/pdf"):
    return SimpleUploadedFile(name, body, content_type=content_type)


def big_pdf(size: int) -> bytes:
    """A PDF-signed blob of a given size, for the upload-limit tests."""
    return MINIMAL_PDF + b"0" * max(0, size - len(MINIMAL_PDF))


@contextmanager
def patched_dispatch(return_value: str = "task-id-stub", side_effect=None):
    """Replace only the network call, leaving payload building real.

    Patches ``dispatch.send`` rather than the Celery app, so the code under test
    still builds a real payload and still goes through ``job_service``.
    """
    with mock.patch(
        "apps.knowledge.dispatch.send", return_value=return_value, side_effect=side_effect
    ) as sender:
        yield sender


class KnowledgeTestCase(TestCase):
    """A staff user and one active knowledge base."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="kb-control",
            email="kb@zionlifts.test",
            password="an-ordinary-long-passphrase-42",
            is_staff=True,
        )
        cls.base = KnowledgeBase.objects.create(
            name="Product manuals", slug="product-manuals", description="Datasheets and manuals."
        )

    def setUp(self):
        # The broker-failure test deliberately provokes a logged traceback.
        # It is the correct behaviour and unreadable noise in a test run.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    @staticmethod
    def upload(name: str = "policy.pdf", body: bytes = MINIMAL_PDF):
        return pdf_upload(name, body)

    @staticmethod
    def stream(body: bytes = MINIMAL_PDF) -> io.BytesIO:
        stream = io.BytesIO(body)
        stream.name = "policy.pdf"
        return stream

    @contextmanager
    def captured_dispatch(self, side_effect=None):
        """Stub the broker *and* run the on-commit callbacks.

        Both halves are needed. ``job_service`` sends after the transaction
        commits, deliberately — a worker must not be able to arrive before the
        rows it describes are visible — and ``TestCase`` wraps each test in a
        transaction it never commits, so without ``captureOnCommitCallbacks``
        the send simply never happens and the test proves nothing.
        """
        with patched_dispatch(side_effect=side_effect) as sender:
            with self.captureOnCommitCallbacks(execute=True):
                yield sender

    def make_ready(self, version, **completion):
        """Walk a version through every stage and publish it.

        The stages are walked rather than skipped because the state machine
        refuses to skip them, which is the property under test elsewhere. This
        is what the worker will do, one report at a time.
        """
        from apps.knowledge.services import version_service
        from apps.knowledge.states import DocumentState

        for stage in (
            DocumentState.EXTRACTING,
            DocumentState.CHUNKING,
            DocumentState.EMBEDDING,
            DocumentState.INDEXING,
        ):
            version.transition_to(stage)
        completion.setdefault("collection", "kb_test__minilm_v1")
        finished = version_service.complete_version(version, **completion)

        # Close the job too. A real worker does; leaving one open would make
        # the next queue() reuse it as "already in flight" and quietly change
        # what the test is exercising.
        for job in version.jobs.all():
            if job.status in ("queued", "running"):
                job.mark_succeeded()
        return finished
