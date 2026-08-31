"""Correlation ids and log redaction on the Django side.

The correlation tests follow one id from an inbound HTTP header through to the
Celery message, because that hop is where a trace usually breaks: both halves
work, and nothing links them.

The redaction tests use fake secrets shaped like real ones. They assert absence,
which is the only assertion that catches this class of bug — a leaked token
raises nothing, it just sits in a log aggregator several teams can read.
"""

from __future__ import annotations

import json
import logging
import uuid
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from zion.observability.context import resolve_request_id, set_request_id
from zion.observability.logging import ConsoleFormatter, JsonFormatter
from zion.observability.middleware import RequestObservabilityMiddleware
from zion.observability.redaction import REDACTED, redact, redact_value, safe_headers

FAKE_SECRETS = {
    "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.fake.signature",
    "api_key": "sk-live-000000000000000000000000",
    "internal_token": "e3b0c44298fc1c149afbf4c8996fb924",
    "password": "hunter2-not-a-real-password",
    "cookie": "sessionid=abc123; csrftoken=def456",
}

HEADER = "X-Request-ID"
META = "HTTP_X_REQUEST_ID"


def run_middleware(request, status_code: int = 200):
    """Drive the middleware over one request and return the response."""
    from django.http import HttpResponse

    middleware = RequestObservabilityMiddleware(
        lambda _request: HttpResponse(status=status_code)
    )
    return middleware(request)


class RequestIdTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_an_id_is_generated_when_the_caller_sends_none(self):
        response = run_middleware(self.factory.get("/api/health/"))
        self.assertTrue(response[HEADER])
        self.assertEqual(len(response[HEADER]), 16)

    def test_a_caller_supplied_id_is_propagated(self):
        request = self.factory.get("/api/health/", **{META: "trace-abc-123"})
        self.assertEqual(run_middleware(request)[HEADER], "trace-abc-123")

    def test_the_id_is_returned_in_the_response_header(self):
        response = run_middleware(self.factory.get("/api/health/"))
        self.assertIn(HEADER, response)

    def test_the_id_is_attached_to_the_request(self):
        request = self.factory.get("/api/health/", **{META: "trace-abc-123"})
        run_middleware(request)
        self.assertEqual(request.request_id, "trace-abc-123")

    def test_an_over_long_id_is_replaced(self):
        # It is echoed onto every line of the request, so a megabyte header must
        # not become a megabyte of logs.
        request = self.factory.get("/api/health/", **{META: "x" * 5000})
        self.assertNotEqual(run_middleware(request)[HEADER], "x" * 5000)

    def test_a_newline_in_the_id_cannot_forge_a_log_line(self):
        hostile = "abc\nWARNING everything is fine"
        request = self.factory.get("/api/health/", **{META: hostile})
        self.assertNotIn("\n", run_middleware(request)[HEADER])

    def test_the_middleware_never_swallows_an_exception(self):
        """Observability must not change what the application does."""
        from django.http import HttpResponse  # noqa: F401

        def boom(_request):
            raise ValueError("the view failed")

        middleware = RequestObservabilityMiddleware(boom)
        with self.assertRaises(ValueError):
            middleware(self.factory.get("/api/health/"))


class ResolveIdTests(SimpleTestCase):
    def test_a_well_formed_id_survives(self):
        self.assertEqual(resolve_request_id("abc-123_XY.z"), "abc-123_XY.z")

    def test_an_empty_id_is_replaced(self):
        self.assertEqual(len(resolve_request_id("")), 16)

    def test_a_hostile_id_is_replaced(self):
        for hostile in ("a b", "a;b", "<script>", "../../etc/passwd", "a\nb"):
            with self.subTest(hostile=hostile):
                self.assertNotEqual(resolve_request_id(hostile), hostile)


class LogRedactionTests(SimpleTestCase):
    def _record(self, **extra) -> logging.LogRecord:
        record = logging.LogRecord(
            "zion.request", logging.INFO, __file__, 1, "request_completed", (), None
        )
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_json_logs_never_carry_a_secret(self):
        rendered = JsonFormatter().format(self._record(**FAKE_SECRETS))
        for value in FAKE_SECRETS.values():
            self.assertNotIn(value, rendered)

    def test_console_logs_never_carry_a_secret(self):
        rendered = ConsoleFormatter().format(self._record(**FAKE_SECRETS))
        for value in FAKE_SECRETS.values():
            self.assertNotIn(value, rendered)

    def test_a_json_line_carries_the_correlation_id(self):
        set_request_id("req-42")
        payload = json.loads(JsonFormatter().format(self._record(duration_ms=12)))
        self.assertEqual(payload["request_id"], "req-42")
        self.assertEqual(payload["service"], "backend")
        self.assertEqual(payload["event"], "request_completed")

    def test_the_two_services_agree_on_field_names(self):
        """One upload crosses both services; the fields must line up.

        A query that has to be written twice because each side spells the
        correlation field differently is a query nobody writes.
        """
        set_request_id("req-42")
        payload = json.loads(JsonFormatter().format(self._record(duration_ms=12)))
        for field in ("ts", "level", "service", "logger", "request_id", "event", "message"):
            self.assertIn(field, payload)

    def test_a_nested_secret_is_found(self):
        payload = {"metadata": {"nested": {"token": FAKE_SECRETS["internal_token"]}}}
        self.assertNotIn(
            FAKE_SECRETS["internal_token"], json.dumps(redact(payload))
        )

    def test_content_is_summarised_not_printed(self):
        summary = redact_value("body", "the confidential shaft width is 1100mm")
        self.assertNotIn("1100mm", summary)
        self.assertIn("sha256:", summary)

    def test_sensitive_request_headers_are_removed(self):
        safe = safe_headers(
            {
                "HTTP_AUTHORIZATION": "Bearer secret-value",
                "HTTP_COOKIE": "sessionid=abc",
                "HTTP_X_INTERNAL_TOKEN": "t" * 40,
                "HTTP_ACCEPT": "application/json",
                "REMOTE_ADDR": "127.0.0.1",
            }
        )
        self.assertEqual(safe["HTTP_AUTHORIZATION"], REDACTED)
        self.assertEqual(safe["HTTP_COOKIE"], REDACTED)
        self.assertEqual(safe["HTTP_X_INTERNAL_TOKEN"], REDACTED)
        self.assertEqual(safe["HTTP_ACCEPT"], "application/json")
        # Not an HTTP header, so it is not in the header view at all.
        self.assertNotIn("REMOTE_ADDR", safe)


class CeleryCorrelationTests(TestCase):
    """The hop where a trace usually breaks: HTTP request -> queue message."""

    def test_the_payload_carries_the_current_correlation_id(self):
        from apps.knowledge import dispatch
        from apps.knowledge.models import Document, DocumentVersion, KnowledgeBase

        set_request_id("trace-from-the-browser")

        base = KnowledgeBase(id=uuid.uuid4(), name="B", slug="b")
        document = Document(id=uuid.uuid4(), knowledge_base=base, name="D")
        version = DocumentVersion(
            id=uuid.uuid4(),
            document=document,
            version_number=1,
            content_hash="a" * 64,
            embedding_model="m",
            embedding_model_version="v1",
        )
        version.file.name = "knowledge/x/v1.pdf"

        payload = dispatch.build_payload(version, job_id=str(uuid.uuid4()))
        self.assertEqual(payload["request_id"], "trace-from-the-browser")
        # Still JSON, still identifiers only — no bytes cross the broker.
        json.dumps(payload)

    def test_a_run_without_an_originating_request_still_produces_a_payload(self):
        """A management command has no HTTP request; ingestion must still work."""
        from apps.knowledge import dispatch
        from apps.knowledge.models import Document, DocumentVersion, KnowledgeBase

        set_request_id("-")
        base = KnowledgeBase(id=uuid.uuid4(), name="B", slug="b")
        document = Document(id=uuid.uuid4(), knowledge_base=base, name="D")
        version = DocumentVersion(
            id=uuid.uuid4(), document=document, version_number=1, content_hash="a" * 64
        )
        version.file.name = "knowledge/x/v1.pdf"

        payload = dispatch.build_payload(version, job_id="job-1")
        self.assertIn("request_id", payload)
        self.assertEqual(payload["job_id"], "job-1")
