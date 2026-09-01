"""The date range every analytics endpoint is asked about.

One parser, used by all of them, so "Last 30 Days" means the same span on the
chart as it does on the summary cards. Getting that wrong is the classic
analytics bug: two panels disagree, and nobody can tell which is lying.

Three things come out of a range, and they are computed together because they
have to agree:

* the **window** itself, as timezone-aware bounds;
* the **previous window** of the same length immediately before it, which is
  what every "↑ 12.4%" on the dashboard is measured against;
* the **granularity** the chart should bucket by, chosen from the span so a day
  is drawn hourly and a year monthly without the client having to ask.

All arithmetic is in the project's local timezone, because "today" is a question
about where the reader is standing, not about UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.utils import timezone

# key -> label, in the order the picker shows them.
PRESETS = {
    "today": "Today",
    "yesterday": "Yesterday",
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "this_month": "This month",
    "last_month": "Last month",
    "12m": "Last 12 months",
    "custom": "Custom range",
}

DEFAULT = "7d"

HOUR, DAY, MONTH = "hour", "day", "month"


class InvalidRange(ValueError):
    """The requested range could not be parsed. The view turns this into a 400."""


@dataclass(frozen=True)
class Range:
    """A resolved window, its comparison window, and how to bucket it."""

    key: str
    label: str
    start: datetime
    end: datetime
    previous_start: datetime
    previous_end: datetime
    granularity: str

    @property
    def days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "granularity": self.granularity,
            "previous_start": self.previous_start,
            "previous_end": self.previous_end,
        }


def parse(params) -> Range:
    """Build a :class:`Range` from query parameters.

    ``?range=<preset>``, or ``?range=custom&start=YYYY-MM-DD&end=YYYY-MM-DD``.
    An unknown preset falls back to the default rather than erroring: a stale
    bookmark should show a dashboard, not a stack trace. A *malformed custom
    range* does error, because there the caller said something specific and
    silently showing them a different week would be worse than a message.
    """
    key = (params.get("range") or DEFAULT).strip().lower()
    if key == "custom":
        start_day, end_day = _custom_days(params)
    elif key in PRESETS:
        start_day, end_day = _preset_days(key)
    else:
        key = DEFAULT
        start_day, end_day = _preset_days(DEFAULT)

    start = _start_of(start_day)
    # Exclusive upper bound at the start of the day *after* the last one, so a
    # single-day range covers the whole day and `created_at < end` needs no
    # off-by-one care at any call site.
    end = _start_of(end_day + timedelta(days=1))

    # A range ending today should not pretend to cover the rest of it: the
    # comparison would measure a part-day against a whole one and report a
    # collapse every morning.
    now = timezone.localtime()
    if end > now:
        end = now

    span = end - start
    return Range(
        key=key,
        label=PRESETS[key],
        start=start,
        end=end,
        previous_start=start - span,
        previous_end=start,
        granularity=granularity_for(span),
    )


def granularity_for(span: timedelta) -> str:
    """Hourly for a day or two, daily up to a quarter, monthly beyond.

    The thresholds are about how many points a chart can carry legibly: 48 hours
    is a readable line, 48 months is not, and roughly 30–90 marks is the band
    where a reader can still follow individual days.
    """
    days = span.total_seconds() / 86400
    if days <= 2:
        return HOUR
    if days <= 92:
        return DAY
    return MONTH


def _preset_days(key: str) -> tuple[date, date]:
    """Inclusive first and last calendar day for a preset."""
    today = timezone.localdate()
    if key == "today":
        return today, today
    if key == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if key == "7d":
        return today - timedelta(days=6), today
    if key == "30d":
        return today - timedelta(days=29), today
    if key == "this_month":
        return today.replace(day=1), today
    if key == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if key == "12m":
        return _months_back(today.replace(day=1), 11), today
    return today - timedelta(days=6), today


def _custom_days(params) -> tuple[date, date]:
    start = _day(params.get("start"), "start")
    end = _day(params.get("end"), "end")
    if start > end:
        start, end = end, start  # a backwards range is a slip, not a refusal
    if (end - start).days > 730:
        raise InvalidRange("A custom range may not be longer than two years.")
    return start, end


def _day(raw, field: str) -> date:
    if not raw:
        raise InvalidRange(f"A custom range needs a {field} date (YYYY-MM-DD).")
    try:
        return date.fromisoformat(str(raw).strip())
    except ValueError:
        raise InvalidRange(f"{field} must be a date in YYYY-MM-DD form.") from None


def _start_of(day: date) -> datetime:
    """Local midnight at the start of ``day``, as an aware datetime."""
    return timezone.make_aware(datetime.combine(day, time.min))


def _months_back(first_of_month: date, months: int) -> date:
    month_index = first_of_month.year * 12 + (first_of_month.month - 1) - months
    return date(month_index // 12, month_index % 12 + 1, 1)
