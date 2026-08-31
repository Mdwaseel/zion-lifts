"""Metrics, redaction and correlation ids.

The tests that matter most here are the negative ones. A metric that is never
recorded and a secret that *is* recorded both fail silently in production — the
first shows up as a chart nobody notices is flat, the second as a credential in
a log aggregator that several teams can read. Neither raises anything, so both
get a test.
"""

from __future__ import annotations

import json
import logging

import pytest

from app.core import events
from app.core.logging import ConsoleFormatter, JsonFormatter, configure_logging
from app.core.metrics import MetricsRegistry, Timer, metrics
from app.core.redaction import REDACTED, redact, redact_headers, redact_value
from app.main import resolve_request_id

FAKE_SECRETS = {
    "api_key": "sk-live-000000000000000000000000",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.fake.signature",
    "internal_token": "e3b0c44298fc1c149afbf4c8996fb924",
    "password": "hunter2-not-a-real-password",
    "cookie": "sessionid=abc123; csrftoken=def456",
    "hf_api_token": "hf_000000000000000000000000000000000000",
}


@pytest.fixture
def registry() -> MetricsRegistry:
    return MetricsRegistry()


class TestMetricsRecording:
    def test_a_counter_accumulates(self, registry):
        registry.increment("chat_requests_total", mode="sync")
        registry.increment("chat_requests_total", mode="sync")
        assert registry.counter("chat_requests_total", mode="sync") == 2

    def test_labels_separate_series(self, registry):
        registry.increment("chat_requests_total", mode="sync")
        registry.increment("chat_requests_total", mode="stream")
        assert registry.counter("chat_requests_total", mode="sync") == 1
        assert registry.counter("chat_requests_total", mode="stream") == 1

    def test_a_histogram_reports_quantiles(self, registry):
        for value in [10, 20, 30, 4000]:
            registry.observe("chat_duration", value)
        summary = registry.histogram("chat_duration").summary()
        assert summary["count"] == 4
        # Bucket edges, not interpolated samples — see Histogram.quantile.
        assert summary["p50_ms"] <= summary["p99_ms"]
        assert summary["max_ms"] == 4000

    def test_a_timer_records_what_it_measured(self, registry, monkeypatch):
        monkeypatch.setattr("app.core.metrics.metrics", registry)
        with Timer("chat_duration", outcome="answered") as timer:
            pass
        assert timer.elapsed_ms >= 0
        assert registry.histogram("chat_duration", outcome="answered") is not None

    def test_disabling_metrics_makes_every_record_a_no_op(self, registry):
        registry.enabled = False
        registry.increment("chat_requests_total")
        registry.observe("chat_duration", 5)
        assert registry.snapshot()["counters"] == {}


class TestMetricsCannotBreakTheCaller:
    """Observability is secondary to correctness; a metric must never raise."""

    def test_a_malformed_name_does_not_raise(self, registry):
        registry.increment("Not A Valid Name!", stage="x")
        registry.observe("also bad", 1.0)

    def test_an_unrecordable_value_does_not_raise(self, registry):
        registry.observe("chat_duration", float("nan"))
        registry.increment("chat_requests_total", value=object())  # type: ignore[arg-type]


class TestLabelCardinality:
    """IDs in labels create one time series per request. Refused, by name."""

    @pytest.mark.parametrize(
        "label",
        ["request_id", "document_id", "user_id", "job_id", "knowledge_base_id", "collection"],
    )
    def test_identifier_labels_are_rejected(self, registry, label):
        registry.increment("chat_requests_total", **{label: "abc-123"})
        assert registry.snapshot()["counters"] == {}
        assert registry.rejected_labels == 1

    def test_an_over_long_label_value_is_rejected(self, registry):
        registry.increment("chat_requests_total", provider="x" * 200)
        assert registry.snapshot()["counters"] == {}

    def test_the_series_count_is_capped(self):
        small = MetricsRegistry(max_series=3)
        for i in range(20):
            small.increment("chat_requests_total", provider=f"p{i}")
        assert len(small.snapshot()["counters"]) == 3
        # The drop is counted rather than silent.
        assert small.dropped_series > 0


class TestRedaction:
    @pytest.mark.parametrize("field,value", sorted(FAKE_SECRETS.items()))
    def test_secret_fields_are_removed(self, field, value):
        assert redact_value(field, value) == REDACTED

    def test_no_secret_survives_a_whole_payload(self):
        rendered = json.dumps(redact(dict(FAKE_SECRETS)))
        for value in FAKE_SECRETS.values():
            assert value not in rendered

    def test_content_is_reduced_to_a_shape_not_removed(self):
        # Useful for telling two values apart; useless for reading one.
        summary = redact_value("text", "the shaft width is 1100mm")
        assert "1100mm" not in summary
        assert "25 chars" in summary and "sha256:" in summary

    def test_the_same_content_summarises_identically(self):
        assert redact_value("answer", "same") == redact_value("answer", "same")
        assert redact_value("answer", "same") != redact_value("answer", "other")

    def test_a_nested_secret_is_found(self):
        # `metadata` is exactly where an unexpected value ends up, so it is
        # walked rather than trusted.
        payload = {"metadata": {"extra": {"api_key": FAKE_SECRETS["api_key"]}}}
        assert FAKE_SECRETS["api_key"] not in json.dumps(redact(payload))

    def test_a_long_unrecognised_value_is_truncated(self):
        rendered = redact_value("note", "x" * 5000)
        assert len(rendered) < 300

    def test_a_long_list_is_summarised_by_length(self):
        assert redact_value("chunks", list(range(900))) == "<900 items>"

    def test_headers_lose_their_credentials_but_keep_their_shape(self):
        safe = redact_headers(
            {"Authorization": "Bearer secret", "X-Api-Key": "k", "Accept": "application/json"}
        )
        assert safe["Authorization"] == REDACTED
        assert safe["X-Api-Key"] == REDACTED
        assert safe["Accept"] == "application/json"


class TestLogRedaction:
    """The formatter is the second line of defence, and it has to hold."""

    def _record(self, **extra) -> logging.LogRecord:
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "chat_completed", (), None)
        for key, value in extra.items():
            setattr(record, key, value)
        record.request_id = "req-1"
        return record

    def test_json_logs_never_carry_a_secret(self):
        rendered = JsonFormatter().format(self._record(**FAKE_SECRETS))
        for value in FAKE_SECRETS.values():
            assert value not in rendered

    def test_console_logs_never_carry_a_secret(self):
        rendered = ConsoleFormatter().format(self._record(**FAKE_SECRETS))
        for value in FAKE_SECRETS.values():
            assert value not in rendered

    def test_a_json_line_carries_the_fields_a_query_filters_on(self):
        configure_logging("INFO", json_output=True, service="ai_service", environment="test")
        payload = json.loads(
            JsonFormatter().format(
                self._record(event=events.CHAT_COMPLETED, duration_ms=182, provider="gemini")
            )
        )
        assert payload["event"] == events.CHAT_COMPLETED
        assert payload["service"] == "ai_service"
        assert payload["request_id"] == "req-1"
        assert payload["duration_ms"] == 182

    def test_the_message_stands_in_when_no_event_was_given(self):
        payload = json.loads(JsonFormatter().format(self._record()))
        assert payload["event"] == "chat_completed"

    def test_a_document_body_is_not_logged_verbatim(self):
        body = "Confidential: the Orion lift shaft is 1100mm."
        rendered = JsonFormatter().format(self._record(text=body))
        assert body not in rendered


class TestCorrelationIds:
    def test_a_well_formed_inbound_id_is_kept(self):
        assert resolve_request_id("abc-123_XY.z", 64) == "abc-123_XY.z"

    def test_a_missing_id_is_generated(self):
        assert len(resolve_request_id(None, 64)) == 16

    def test_an_over_long_id_is_replaced(self):
        # It is echoed onto every line of the request; a megabyte header must
        # not become a megabyte of logs.
        assert resolve_request_id("x" * 5000, 64) != "x" * 5000

    @pytest.mark.parametrize(
        "hostile",
        [
            "abc\ndef",  # forged log lines
            "abc def",
            "a;rm -rf /",
            "<script>alert(1)</script>",
            "../../etc/passwd",
        ],
    )
    def test_a_hostile_id_is_never_echoed(self, hostile):
        resolved = resolve_request_id(hostile, 64)
        assert resolved != hostile
        assert len(resolved) == 16


class TestProcessRegistry:
    def test_the_shared_registry_is_usable_and_resettable(self):
        metrics.reset()
        metrics.increment("chat_requests_total", mode="sync")
        assert metrics.counter("chat_requests_total", mode="sync") == 1
        metrics.reset()
        assert metrics.counter("chat_requests_total", mode="sync") == 0
