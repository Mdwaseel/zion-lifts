"""A small, in-process metrics registry.

Deliberately not a monitoring client. The three operations below —
``increment``, ``observe``, ``set_gauge`` — are the whole vocabulary, so the
modules that call them stay ignorant of where the numbers eventually go, and
swapping in Prometheus or StatsD later means writing one exporter rather than
editing every call site.

Three properties are load-bearing:

*It cannot break the caller.* Every public function swallows its own exceptions.
A metric is an observation about work, never a participant in it: an ingestion
run must not fail because a counter name was malformed. This is the one place in
the codebase where a bare ``except`` is the correct thing to write.

*It cannot be made unbounded.* Labels are validated against a deny-list of
identifier-shaped names and the series count is capped. A metrics backend keeps
one time series per distinct label combination, so labelling by ``request_id``
does not produce a useful chart — it produces a million charts and an outage in
whatever is storing them. Identifiers belong in logs, which are read one at a
time and expire.

*It costs nothing per call.* An increment takes a lock and adds an integer.
There is no network, no disk, and no database — see the note about what
observability must never do to the thing it is observing.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from threading import Lock
from typing import Final

# Label values must be low-cardinality: a bounded set an operator could list.
# These names are not, and each one has burned somebody: labelling by request id
# or document id creates a fresh time series per request or per document.
_FORBIDDEN_LABELS: Final = frozenset(
    {
        "request_id",
        "correlation_id",
        "trace_id",
        "user_id",
        "user",
        "email",
        "document_id",
        "document_version_id",
        "knowledge_base_id",
        "job_id",
        "task_id",
        "chunk_id",
        "collection",
        "query",
        "prompt",
        "text",
        "url",
        "path",
        "filename",
        "content_hash",
    }
)

# Anything longer than this is not a category, whatever it is called.
_MAX_LABEL_VALUE = 64

# The ceiling on distinct series. Reaching it means a label is varying more than
# intended; new series are dropped rather than allowed to exhaust memory, and
# the drop is counted so the gap is visible instead of silent.
_MAX_SERIES: Final = 2048

_SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

# Millisecond boundaries, spanning a fast cache hit to a slow scanned PDF.
# Fixed buckets rather than stored samples: quantiles come out of counts, so
# memory is constant no matter how many observations arrive.
_DEFAULT_BUCKETS: Final = (
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    2500.0,
    5000.0,
    10_000.0,
    30_000.0,
    60_000.0,
    300_000.0,
)


def _key(name: str, labels: dict[str, str]) -> str:
    if not labels:
        return name
    rendered = ",".join(f"{k}={labels[k]}" for k in sorted(labels))
    return f"{name}{{{rendered}}}"


class Histogram:
    """Bucketed durations, plus the count/sum/min/max worth reporting exactly."""

    __slots__ = ("buckets", "counts", "count", "total", "minimum", "maximum")

    def __init__(self, buckets: tuple[float, ...] = _DEFAULT_BUCKETS) -> None:
        self.buckets = buckets
        self.counts = [0] * (len(buckets) + 1)  # the extra slot is +Inf
        self.count = 0
        self.total = 0.0
        self.minimum = math.inf
        self.maximum = -math.inf

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)
        for i, edge in enumerate(self.buckets):
            if value <= edge:
                self.counts[i] += 1
                return
        self.counts[-1] += 1

    def quantile(self, q: float) -> float | None:
        """The bucket edge at which the qth quantile falls.

        Approximate, and honestly so: the return value is a bucket boundary, not
        an interpolated sample. That is the right trade for alerting — "p95 is
        above 2.5s" is actionable, and the extra precision an exact quantile
        would give does not change what an operator does about it.
        """
        if not self.count:
            return None
        target = q * self.count
        seen = 0
        for i, edge in enumerate(self.buckets):
            seen += self.counts[i]
            if seen >= target:
                return edge
        return math.inf if self.counts[-1] else self.buckets[-1]

    def summary(self) -> dict[str, float | None]:
        return {
            "count": self.count,
            "sum_ms": round(self.total, 2),
            "avg_ms": round(self.total / self.count, 2) if self.count else None,
            "min_ms": round(self.minimum, 2) if self.count else None,
            "max_ms": round(self.maximum, 2) if self.count else None,
            "p50_ms": self.quantile(0.50),
            "p95_ms": self.quantile(0.95),
            "p99_ms": self.quantile(0.99),
        }


class MetricsRegistry:
    """Counters, histograms and gauges, held in memory for this process.

    Per process, and that is a real limitation rather than an oversight: with
    several API workers and several Celery children, each holds its own numbers.
    The exporter is what aggregates them, exactly as a Prometheus scrape does.
    """

    def __init__(self, enabled: bool = True, max_series: int = _MAX_SERIES) -> None:
        self.enabled = enabled
        self._max_series = max_series
        self._lock = Lock()
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, Histogram] = {}
        self._gauges: dict[str, float] = {}
        # Rejections are themselves a signal: a rising number means a call site
        # is passing something it should not.
        self.rejected_labels = 0
        self.dropped_series = 0

    # --- validation ----------------------------------------------------------

    def _clean_labels(self, labels: dict[str, object]) -> dict[str, str] | None:
        cleaned: dict[str, str] = {}
        for raw_key, raw_value in labels.items():
            key = str(raw_key).lower()
            if key in _FORBIDDEN_LABELS or not _SAFE_NAME.match(key):
                self.rejected_labels += 1
                return None
            if raw_value is None:
                continue
            value = str(raw_value)
            if len(value) > _MAX_LABEL_VALUE:
                self.rejected_labels += 1
                return None
            cleaned[key] = value
        return cleaned

    def _room_for(self, store: Mapping[str, object], key: str) -> bool:
        if key in store:
            return True
        if len(store) >= self._max_series:
            self.dropped_series += 1
            return False
        return True

    # --- recording -----------------------------------------------------------

    def increment(self, name: str, value: float = 1.0, **labels: object) -> None:
        if not self.enabled:
            return
        try:
            clean = self._clean_labels(labels)
            if clean is None:
                return
            key = _key(name, clean)
            with self._lock:
                if not self._room_for(self._counters, key):
                    return
                self._counters[key] = self._counters.get(key, 0.0) + value
        except Exception:  # pragma: no cover - a metric must never raise
            pass

    def observe(self, name: str, value: float, **labels: object) -> None:
        """Record a duration in milliseconds."""
        if not self.enabled:
            return
        try:
            clean = self._clean_labels(labels)
            if clean is None:
                return
            key = _key(name, clean)
            with self._lock:
                if not self._room_for(self._histograms, key):
                    return
                histogram = self._histograms.get(key)
                if histogram is None:
                    histogram = self._histograms[key] = Histogram()
                histogram.observe(float(value))
        except Exception:  # pragma: no cover
            pass

    def set_gauge(self, name: str, value: float, **labels: object) -> None:
        if not self.enabled:
            return
        try:
            clean = self._clean_labels(labels)
            if clean is None:
                return
            key = _key(name, clean)
            with self._lock:
                if not self._room_for(self._gauges, key):
                    return
                self._gauges[key] = float(value)
        except Exception:  # pragma: no cover
            pass

    # --- reading -------------------------------------------------------------

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": dict(sorted(self._counters.items())),
                "histograms": {
                    key: self._histograms[key].summary() for key in sorted(self._histograms)
                },
                "gauges": dict(sorted(self._gauges.items())),
                "meta": {
                    "series": len(self._counters) + len(self._histograms) + len(self._gauges),
                    "max_series": self._max_series,
                    "rejected_labels": self.rejected_labels,
                    "dropped_series": self.dropped_series,
                },
            }

    def counter(self, name: str, **labels: object) -> float:
        """One counter's value. For tests and the ops endpoint."""
        clean = self._clean_labels(labels) or {}
        with self._lock:
            return self._counters.get(_key(name, clean), 0.0)

    def histogram(self, name: str, **labels: object) -> Histogram | None:
        clean = self._clean_labels(labels) or {}
        with self._lock:
            return self._histograms.get(_key(name, clean))

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
            self.rejected_labels = 0
            self.dropped_series = 0


# The process-wide registry. A module-level singleton because metrics are a
# property of the process, and threading one through every constructor would
# put an observability concern into the signature of every business object.
metrics = MetricsRegistry()


def configure_metrics(enabled: bool) -> None:
    metrics.enabled = enabled


class Timer:
    """Measure a block and record it, in milliseconds.

    ``elapsed_ms`` is readable afterwards so the same measurement can go into a
    log line's fields without timing the work twice::

        with Timer("chat_stage_duration", stage="rerank") as t:
            chunks = await rerank(...)
        logger.info(events.RERANKING_COMPLETED, extra={"duration_ms": t.elapsed_ms})
    """

    __slots__ = ("_name", "_labels", "_started", "elapsed_ms")

    def __init__(self, name: str, **labels: object) -> None:
        self._name = name
        self._labels = labels
        self._started = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self) -> Timer:
        from time import perf_counter

        self._started = perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        from time import perf_counter

        self.elapsed_ms = (perf_counter() - self._started) * 1000
        metrics.observe(self._name, self.elapsed_ms, **self._labels)
