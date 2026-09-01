"""Every question the dashboard asks, as one aggregate query each.

The rule this module follows: **one panel, one round trip, no Python loops over
rows.** Counting in Django and summing in a for-loop is how an analytics screen
that was fine with ten thousand page views becomes a timeout at ten million. If
a function here returns a list, it came back from the database that shape.

Which table answers which question is decided by where the column lives (see
``models.py``): anything about *the visit* — device, browser, OS, country,
traffic source, bounce, duration — reads ``Session``, one row per visit.
Anything about *a page* reads ``PageView``. That is why the device chart is
cheap even when the page-view table is enormous.

Everything these functions count was written by a real visitor. There is no
seeder and no demo flag in this app, so no query here needs a filter to exclude
synthetic rows — an empty result means nobody visited, and that is what the
dashboard reports.
"""

from __future__ import annotations

from django.db.models import Avg, Count, F, Q, QuerySet
from django.db.models.functions import TruncDay, TruncHour, TruncMonth
from django.utils import timezone

from .models import Channel, Device, PageView, Session, Visitor, online_window_minutes
from .ranges import DAY, HOUR, MONTH, Range

TRUNCATE = {HOUR: TruncHour, DAY: TruncDay, MONTH: TruncMonth}


def views_in(start, end) -> QuerySet[PageView]:
    return PageView.objects.filter(created_at__gte=start, created_at__lt=end)


def sessions_in(start, end) -> QuerySet[Session]:
    return Session.objects.filter(started_at__gte=start, started_at__lt=end)


def visitors_first_seen_in(start, end) -> QuerySet[Visitor]:
    return Visitor.objects.filter(first_seen__gte=start, first_seen__lt=end)


def has_any_data() -> bool:
    """Whether a single page view has ever been recorded.

    Drives the dashboard's empty state, and it is a question about the whole
    table rather than the selected window: "nobody has visited yet" and "nobody
    visited last Tuesday" want different words on screen.
    """
    return PageView.objects.exists()


# --------------------------------------------------------------------- totals
def totals(start, end) -> dict:
    """The core counts for one window, in two queries.

    Unique visitors is a ``COUNT(DISTINCT visitor_id)`` over page views rather
    than a count of sessions: one person visiting three times is one visitor and
    three visits, and conflating them is the second-classic analytics bug.
    """
    views = views_in(start, end).aggregate(
        page_views=Count("id"),
        visitors=Count("visitor_id", distinct=True),
    )
    visits = sessions_in(start, end).aggregate(
        sessions=Count("id"),
        bounced=Count("id", filter=Q(page_view_count__lte=1)),
        pages_per_session=Avg("page_view_count"),
        # Duration is derived in SQL from the two timestamps we already store,
        # so there is no third column to keep consistent with them.
        duration=Avg(F("last_activity_at") - F("started_at")),
    )

    sessions = visits["sessions"] or 0
    duration = visits["duration"]
    return {
        "visitors": views["visitors"] or 0,
        "page_views": views["page_views"] or 0,
        "sessions": sessions,
        "bounce_rate": _pct(visits["bounced"] or 0, sessions),
        "pages_per_session": round(visits["pages_per_session"] or 0, 2),
        "avg_session_seconds": int(duration.total_seconds()) if duration else 0,
    }


def visitor_mix(start, end) -> dict:
    """New versus returning, counted on people rather than on visits."""
    total = views_in(start, end).aggregate(n=Count("visitor_id", distinct=True))["n"] or 0
    new = visitors_first_seen_in(start, end).count()
    # A visitor whose first-ever view is inside the window is new; everyone else
    # seen in it has been here before. Clamped because the two queries run a
    # moment apart and an arrival in between must not produce a negative.
    new = min(new, total)
    return {"total": total, "new": new, "returning": total - new}


def live() -> dict:
    """Who is here right now, and what they just looked at."""
    since = timezone.now() - timezone.timedelta(minutes=online_window_minutes())
    online = (
        Session.objects.filter(last_activity_at__gte=since)
        .values("visitor_id")
        .distinct()
        .count()
    )
    return {"online": online, "window_minutes": online_window_minutes()}


# ----------------------------------------------------------------- timeseries
def timeseries(window: Range) -> list[dict]:
    """Visitors and page views per bucket, gap-filled across the whole window.

    Two grouped queries, then a merge over the *expected* buckets rather than
    over the returned rows. Gap-filling matters: a quiet Sunday returns no row
    at all, and a chart that simply omits it draws Monday next to Saturday and
    silently flattens the week.
    """
    trunc = TRUNCATE[window.granularity]
    rows = (
        views_in(window.start, window.end)
        .annotate(bucket=trunc("created_at"))
        .values("bucket")
        .annotate(page_views=Count("id"), visitors=Count("visitor_id", distinct=True))
    )
    found = {row["bucket"]: row for row in rows}

    out = []
    for bucket in _buckets(window):
        row = found.get(bucket)
        out.append(
            {
                "bucket": bucket,
                "visitors": row["visitors"] if row else 0,
                "page_views": row["page_views"] if row else 0,
            }
        )
    return out


def _buckets(window: Range) -> list:
    """Every bucket start the window covers, in local time."""
    step = window.granularity
    current = timezone.localtime(window.start)
    if step == HOUR:
        current = current.replace(minute=0, second=0, microsecond=0)
    else:
        current = current.replace(hour=0, minute=0, second=0, microsecond=0)
        if step == MONTH:
            current = current.replace(day=1)

    end = window.end
    out = []
    # Bounded so a bad range cannot spin: 800 is well past any granularity's
    # legible maximum (a two-year custom range is ~731 daily buckets).
    while current < end and len(out) < 800:
        out.append(current)
        current = _advance(current, step)
    return out


def _advance(moment, step: str):
    if step == HOUR:
        return moment + timezone.timedelta(hours=1)
    if step == DAY:
        return moment + timezone.timedelta(days=1)
    # Months are not a fixed length, so step by calendar rather than by delta.
    year, month = moment.year, moment.month
    return moment.replace(year=year + month // 12, month=month % 12 + 1, day=1)


# ---------------------------------------------------------------------- pages
def top_pages(start, end, *, limit: int = 10, offset: int = 0) -> list[dict]:
    """The most-viewed paths, with the per-page numbers the table shows.

    All five columns come from one grouped query. ``avg_seconds`` ignores the
    nulls that the last view of each visit leaves behind — that is Django's
    default for ``Avg`` and it is the correct behaviour here: an unknown
    duration should not be averaged in as a zero.
    """
    rows = (
        views_in(start, end)
        .values("path")
        .annotate(
            views=Count("id"),
            visitors=Count("visitor_id", distinct=True),
            avg_seconds=Avg("duration_seconds"),
            # A bounce is a property of the *visit*, so it is counted on the
            # entry page: the page someone landed on and left from is the one
            # that failed to hold them.
            entries=Count("session_id", filter=Q(session__entry_path=F("path")), distinct=True),
            bounces=Count(
                "session_id",
                filter=Q(session__entry_path=F("path"), session__page_view_count__lte=1),
                distinct=True,
            ),
        )
        .order_by("-views")[offset : offset + limit]
    )
    return [
        {
            "path": row["path"],
            "views": row["views"],
            "visitors": row["visitors"],
            "avg_seconds": int(row["avg_seconds"] or 0),
            "bounce_rate": _pct(row["bounces"], row["entries"]),
        }
        for row in rows
    ]


def count_pages(start, end) -> int:
    """Distinct paths in the window — the pager's total."""
    return views_in(start, end).values("path").distinct().count()


def page_detail(start, end, path: str, window: Range) -> dict:
    """Everything the drill-in screen for one page needs."""
    scoped = views_in(start, end).filter(path=path)
    summary = scoped.aggregate(
        views=Count("id"),
        visitors=Count("visitor_id", distinct=True),
        avg_seconds=Avg("duration_seconds"),
    )
    entries = sessions_in(start, end).filter(entry_path=path)
    entry_stats = entries.aggregate(
        landings=Count("id"),
        bounces=Count("id", filter=Q(page_view_count__lte=1)),
    )

    trunc = TRUNCATE[window.granularity]
    rows = (
        scoped.annotate(bucket=trunc("created_at"))
        .values("bucket")
        .annotate(page_views=Count("id"), visitors=Count("visitor_id", distinct=True))
    )
    found = {row["bucket"]: row for row in rows}
    series = [
        {
            "bucket": bucket,
            "visitors": found[bucket]["visitors"] if bucket in found else 0,
            "page_views": found[bucket]["page_views"] if bucket in found else 0,
        }
        for bucket in _buckets(window)
    ]

    return {
        "path": path,
        "views": summary["views"] or 0,
        "visitors": summary["visitors"] or 0,
        "avg_seconds": int(summary["avg_seconds"] or 0),
        "landings": entry_stats["landings"] or 0,
        "bounce_rate": _pct(entry_stats["bounces"] or 0, entry_stats["landings"] or 0),
        "series": series,
        # Where people went from here, which is the question a page detail
        # screen exists to answer.
        "next_pages": _next_pages(start, end, path),
        "devices": breakdown(start, end, "device", labels=dict(Device.choices)),
        "channels": breakdown(start, end, "channel", labels=dict(Channel.choices)),
    }


def _next_pages(start, end, path: str, limit: int = 5) -> list[dict]:
    """The paths most often viewed in the same visit as this one, excluding it."""
    session_ids = views_in(start, end).filter(path=path).values("session_id")
    rows = (
        views_in(start, end)
        .filter(session_id__in=session_ids)
        .exclude(path=path)
        .values("path")
        .annotate(views=Count("id"))
        .order_by("-views")[:limit]
    )
    return list(rows)


# ----------------------------------------------------------------- dimensions
def breakdown(start, end, field: str, *, labels: dict | None = None, limit: int = 8) -> list[dict]:
    """Visitors and page views grouped by one session column.

    Serves devices, browsers, operating systems and traffic sources — they are
    the same query with a different GROUP BY, so they are one function. Rows
    beyond ``limit`` are folded into "Other" rather than dropped, because a
    chart whose slices do not sum to the total is a chart that gets queried.
    """
    rows = list(
        sessions_in(start, end)
        .values(field)
        .annotate(visitors=Count("visitor_id", distinct=True), sessions=Count("id"))
        .order_by("-visitors")
    )
    total = sum(row["visitors"] for row in rows) or 0

    head, tail = rows[:limit], rows[limit:]
    out = [
        {
            "key": row[field] or "unknown",
            "label": (labels or {}).get(row[field]) or (row[field] or "Other"),
            "visitors": row["visitors"],
            "sessions": row["sessions"],
            "percentage": _pct(row["visitors"], total),
        }
        for row in head
    ]
    if tail:
        folded = sum(row["visitors"] for row in tail)
        out.append(
            {
                "key": "other",
                "label": "Other",
                "visitors": folded,
                "sessions": sum(row["sessions"] for row in tail),
                "percentage": _pct(folded, total),
            }
        )
    return out


def devices(start, end) -> list[dict]:
    return breakdown(start, end, "device", labels=dict(Device.choices))


def browsers(start, end) -> list[dict]:
    return breakdown(start, end, "browser", limit=5)


def operating_systems(start, end) -> list[dict]:
    return breakdown(start, end, "os", limit=6)


def channels(start, end) -> list[dict]:
    return breakdown(start, end, "channel", labels=dict(Channel.choices))


def referrers(start, end, limit: int = 8) -> list[dict]:
    """The actual domains behind the referral and search channels."""
    rows = (
        sessions_in(start, end)
        .exclude(referrer_host="")
        .values("referrer_host", "channel")
        .annotate(visitors=Count("visitor_id", distinct=True))
        .order_by("-visitors")[:limit]
    )
    return [
        {
            "host": row["referrer_host"],
            "channel": row["channel"],
            "visitors": row["visitors"],
        }
        for row in rows
    ]


# ----------------------------------------------------------------- geography
def geography(start, end, *, level: str = "country", limit: int = 20) -> list[dict]:
    """Visitors and page views by country, region or city.

    Rows with no location are excluded rather than bucketed as "Unknown": geo is
    only populated when a proxy resolved it (see ``geo.py``), so on a deployment
    without one this correctly returns nothing at all and the panel says so,
    instead of drawing a single 100% "Unknown" bar that looks like a bug.
    """
    field = {"country": "country", "region": "region", "city": "city"}.get(level, "country")
    rows = (
        sessions_in(start, end)
        .exclude(**{field: ""})
        .values(field)
        .annotate(
            visitors=Count("visitor_id", distinct=True),
            page_views=Count("page_views"),
        )
        .order_by("-visitors")[:limit]
    )
    return [
        {
            "name": row[field],
            "visitors": row["visitors"],
            "page_views": row["page_views"],
        }
        for row in rows
    ]


def geography_available() -> bool:
    """Whether any session has ever carried a country, for the empty state."""
    return Session.objects.exclude(country="").exists()


# ------------------------------------------------------------------- activity
def recent_activity(limit: int = 25, offset: int = 0) -> list[dict]:
    """The live feed: the newest page views with their visit's dimensions.

    ``select_related`` on the session is what keeps this one query instead of
    ``limit + 1`` — this endpoint is polled every few seconds, so an N+1 here
    would be an N+1 forever.

    No visitor key, no IP, nothing that identifies a person: a feed like this is
    read over someone's shoulder, and "who is on the site right now" is not a
    question the panel should be able to answer about an individual.
    """
    rows = (
        PageView.objects.select_related("session")
        .order_by("-created_at")[offset : offset + limit]
    )
    return [
        {
            "id": view.id,
            "path": view.path,
            "at": view.created_at,
            "device": view.session.get_device_display(),
            "channel": view.session.get_channel_display(),
            "browser": view.session.browser,
            "location": _location(view.session),
        }
        for view in rows
    ]


def count_activity() -> int:
    return PageView.objects.count()


def _location(session: Session) -> str:
    parts = [session.city, session.country]
    return ", ".join(part for part in parts if part)


# --------------------------------------------------------------------- shared
def _pct(part: int, whole: int) -> float:
    return round(part * 100 / whole, 1) if whole else 0.0


def change(current: float, previous: float) -> float | None:
    """Percentage movement between two periods.

    ``None`` when the previous period was empty. That is not zero and not
    "+100%": there is no meaningful percentage change from nothing, and showing
    one is how a dashboard reports a triumphant ↑ on its first day of data.
    """
    if not previous:
        return None
    return round((current - previous) * 100 / previous, 1)
