"""Shaping selector output into what the dashboard renders.

Plain functions rather than DRF serializers: nothing here maps to a model
instance or validates input — these are aggregate rows on their way out, and a
``ModelSerializer`` over a ``values()`` dict is ceremony with no payoff.

The one rule worth naming: **formatting that the client would otherwise have to
reinvent happens here.** A duration is sent both as seconds and as "3m 42s", a
bucket both as an ISO timestamp and as the label the axis should print. Two
clients formatting the same seconds two ways is how a dashboard ends up
disagreeing with its own tooltip.
"""

from __future__ import annotations

from django.utils import timezone

from .. import selectors
from ..ranges import DAY, HOUR, MONTH, PRESETS, Range


def duration(seconds: int | None) -> str:
    """``3m 42s`` — the form the cards and tables print."""
    total = int(seconds or 0)
    if total <= 0:
        return "0s"
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def range_payload(window: Range) -> dict:
    return {
        "key": window.key,
        "label": window.label,
        "start": window.start,
        "end": window.end,
        "granularity": window.granularity,
        "previous_start": window.previous_start,
        "previous_end": window.previous_end,
        "presets": [{"key": key, "label": label} for key, label in PRESETS.items()],
    }


def _card(key, label, value, *, description, display=None, current=None, previous=None, live=False):
    """One summary card.

    ``change`` is null when there is no previous period to compare against, and
    the card renders nothing rather than a fabricated arrow — see
    ``selectors.change``.
    """
    delta = None if current is None else selectors.change(current, previous or 0)
    return {
        "key": key,
        "label": label,
        "value": value,
        "display": display if display is not None else f"{value:,}",
        "description": description,
        "change": delta,
        "direction": None if delta is None else ("up" if delta >= 0 else "down"),
        "is_live": live,
    }


def cards_payload(*, current, previous, today, week, month, live) -> list[dict]:
    """The eight cards across the top, in the order they are shown."""
    return [
        _card(
            "visitors", "Total visitors", current["visitors"],
            description="Unique people in this period",
            current=current["visitors"], previous=previous["visitors"],
        ),
        _card(
            "page_views", "Total page views", current["page_views"],
            description="Pages opened in this period",
            current=current["page_views"], previous=previous["page_views"],
        ),
        _card(
            "visitors_today", "Visitors today", today["visitors"],
            description="Unique people since midnight",
        ),
        _card(
            "page_views_today", "Page views today", today["page_views"],
            description="Pages opened since midnight",
        ),
        _card(
            "visitors_week", "Visitors this week", week["visitors"],
            description="Unique people in the last 7 days",
        ),
        _card(
            "visitors_month", "Visitors this month", month["visitors"],
            description="Unique people since the 1st",
        ),
        _card(
            "online", "Online now", live["online"],
            description=f"Active in the last {live['window_minutes']} minutes",
            live=True,
        ),
        _card(
            "avg_session", "Avg. session duration", current["avg_session_seconds"],
            display=duration(current["avg_session_seconds"]),
            description="Time from first to last page of a visit",
            current=current["avg_session_seconds"],
            previous=previous["avg_session_seconds"],
        ),
    ]


def series_payload(rows: list[dict], granularity: str) -> list[dict]:
    """Chart points, each carrying the label its axis and tooltip should print."""
    return [
        {
            "bucket": row["bucket"],
            "label": bucket_label(row["bucket"], granularity),
            "full_label": bucket_label(row["bucket"], granularity, full=True),
            "visitors": row["visitors"],
            "page_views": row["page_views"],
        }
        for row in rows
    ]


def bucket_label(moment, granularity: str, *, full: bool = False) -> str:
    """Axis text for a bucket. ``full`` is the longer form the tooltip shows.

    The day number is trimmed by hand rather than with ``%-d``: that flag is a
    glibc extension, and it raises ``ValueError`` on Windows — where this is
    developed — so the portable spelling is the only one that runs everywhere
    the project does.
    """
    local = timezone.localtime(moment)
    day = str(local.day)
    if granularity == HOUR:
        return f"{day} {local:%b}, {local:%H:%M}" if full else f"{local:%H:%M}"
    if granularity == DAY:
        return f"{local:%A} {day} {local:%B %Y}" if full else f"{day} {local:%b}"
    if granularity == MONTH:
        return f"{local:%B %Y}" if full else f"{local:%b %y}"
    return local.isoformat()


def page_detail_payload(detail: dict, granularity: str) -> dict:
    return {
        **detail,
        "avg_time": duration(detail["avg_seconds"]),
        "series": series_payload(detail["series"], granularity),
    }


def activity_payload(rows: list[dict]) -> list[dict]:
    """The live feed, with a clock face and a relative age per row."""
    now = timezone.now()
    return [
        {
            **row,
            "time": _clock(timezone.localtime(row["at"])),
            "ago": _ago(now - row["at"]),
        }
        for row in rows
    ]


def _clock(local) -> str:
    """``10:42 AM``. Hand-trimmed for the same reason as the day above."""
    return f"{local.hour % 12 or 12}:{local:%M %p}"


def _ago(delta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def export_rows(window: Range) -> list[list]:
    """The CSV: one section per panel, which is what a report is read as.

    A single flat table cannot hold "visitors by device" and "views by page" at
    once without a discriminator column nobody wants, so the export mirrors the
    dashboard's sections instead. Every spreadsheet handles blank-line-separated
    blocks; a normalised long format would be tidier and less usable.
    """
    start, end = window.start, window.end
    totals = selectors.totals(start, end)
    mix = selectors.visitor_mix(start, end)
    previous = selectors.totals(window.previous_start, window.previous_end)

    rows: list[list] = [
        ["Zion Lifts — website analytics"],
        ["Range", window.label],
        ["From", timezone.localtime(start).strftime("%Y-%m-%d %H:%M")],
        ["To", timezone.localtime(end).strftime("%Y-%m-%d %H:%M")],
        ["Generated", timezone.localtime().strftime("%Y-%m-%d %H:%M")],
        [],
        ["Summary", "Value", "Previous period"],
        ["Unique visitors", totals["visitors"], previous["visitors"]],
        ["Page views", totals["page_views"], previous["page_views"]],
        ["Sessions", totals["sessions"], previous["sessions"]],
        ["New visitors", mix["new"], ""],
        ["Returning visitors", mix["returning"], ""],
        ["Pages per session", totals["pages_per_session"], previous["pages_per_session"]],
        ["Avg. session duration", duration(totals["avg_session_seconds"]),
         duration(previous["avg_session_seconds"])],
        ["Bounce rate %", totals["bounce_rate"], previous["bounce_rate"]],
        [],
        ["Top pages", "Views", "Visitors", "Avg. time", "Bounce rate %"],
    ]
    rows += [
        [row["path"], row["views"], row["visitors"], duration(row["avg_seconds"]), row["bounce_rate"]]
        for row in selectors.top_pages(start, end, limit=50)
    ]

    for title, data in (
        ("Traffic sources", selectors.channels(start, end)),
        ("Devices", selectors.devices(start, end)),
        ("Browsers", selectors.browsers(start, end)),
        ("Operating systems", selectors.operating_systems(start, end)),
    ):
        rows += [[], [title, "Visitors", "Share %"]]
        rows += [[row["label"], row["visitors"], row["percentage"]] for row in data]

    return rows
