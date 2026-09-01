"""The admin analytics API. Staff only, every endpoint.

One panel per endpoint, so a slow section cannot hold up the rest of the screen
and the dashboard's date picker can refetch exactly what changed. They share
three things: the same range parser, the same staff gate, and the same
short-lived cache.

**On caching.** Aggregates over a fixed historical window do not change, and the
window that includes today changes slowly compared to how often somebody clicks
between tabs. Sixty seconds of cache turns a dashboard that re-runs a dozen
aggregates on every interaction into one that runs them once a minute. Realtime
is deliberately excluded — a live feed that is a minute stale is not live.

Every number these endpoints return is counted from rows a real visitor created.
There is nothing here that substitutes a placeholder for an empty table: zero
visitors is reported as zero, and ``has_data`` tells the dashboard to explain
why rather than to invent something.
"""

from __future__ import annotations

import hashlib
import json

from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.adminpanel.permissions import IsAdminPanelUser

from .. import ranges, selectors
from ..models import Channel, Device
from . import serializers as api_serializers

CACHE_SECONDS = 60


class AnalyticsView(APIView):
    """Base: staff-only, range-aware, cached.

    Subclasses implement :meth:`payload` and get the rest. ``cache_key_parts``
    lets a view that reads extra query parameters — a page number, a page path
    — keep them out of each other's cache entries.
    """

    permission_classes = [IsAdminPanelUser]
    cache_seconds = CACHE_SECONDS

    def get(self, request):
        try:
            window = ranges.parse(request.query_params)
        except ranges.InvalidRange as error:
            return Response({"detail": str(error)}, status=400)

        key = self._cache_key(request, window)
        if key:
            cached = cache.get(key)
            if cached is not None:
                return Response(cached)

        payload = self.payload(request, window)
        if key:
            cache.set(key, payload, self.cache_seconds)
        return Response(payload)

    def payload(self, request, window: ranges.Range) -> dict:
        raise NotImplementedError

    def cache_key_parts(self, request) -> tuple:
        return ()

    def _cache_key(self, request, window) -> str | None:
        if not self.cache_seconds:
            return None
        raw = json.dumps(
            [
                self.__class__.__name__,
                window.key,
                window.start.isoformat(),
                window.end.isoformat(),
                *self.cache_key_parts(request),
            ],
            default=str,
        )
        return f"analytics:{hashlib.sha256(raw.encode()).hexdigest()[:32]}"


def _meta(window: ranges.Range) -> dict:
    """The envelope every response carries, so the client can render honestly."""
    return {
        "range": api_serializers.range_payload(window),
        # Whether the site has *ever* been visited, which is a different question
        # from whether it was visited in the selected window — the dashboard
        # words the two empty states differently.
        "has_data": selectors.has_any_data(),
    }


class OverviewView(AnalyticsView):
    """``/overview/`` — the summary cards and the traffic overview panel."""

    def payload(self, request, window):
        current = selectors.totals(window.start, window.end)
        previous = selectors.totals(window.previous_start, window.previous_end)
        mix = selectors.visitor_mix(window.start, window.end)

        today_start = ranges.parse({"range": "today"})
        week = ranges.parse({"range": "7d"})
        month = ranges.parse({"range": "this_month"})

        return {
            **_meta(window),
            "cards": api_serializers.cards_payload(
                current=current,
                previous=previous,
                today=selectors.totals(today_start.start, today_start.end),
                week=selectors.totals(week.start, week.end),
                month=selectors.totals(month.start, month.end),
                live=selectors.live(),
            ),
            "traffic": {
                **current,
                "new_visitors": mix["new"],
                "returning_visitors": mix["returning"],
                "new_share": round(mix["new"] * 100 / mix["total"], 1) if mix["total"] else 0.0,
            },
            "previous": previous,
        }


class VisitorsView(AnalyticsView):
    """``/visitors/`` — the timeseries behind the main chart."""

    def payload(self, request, window):
        return {
            **_meta(window),
            "granularity": window.granularity,
            "series": api_serializers.series_payload(
                selectors.timeseries(window), window.granularity
            ),
        }


class PagesView(AnalyticsView):
    """``/pages/`` — Top Pages, paginated, or one page's detail via ``?path=``."""

    def cache_key_parts(self, request):
        return (
            request.query_params.get("page", "1"),
            request.query_params.get("page_size", "10"),
            request.query_params.get("path", ""),
        )

    def payload(self, request, window):
        path = request.query_params.get("path")
        if path:
            return {
                **_meta(window),
                "detail": api_serializers.page_detail_payload(
                    selectors.page_detail(window.start, window.end, path, window),
                    window.granularity,
                ),
            }

        page, page_size = _paging(request, default_size=10, max_size=100)
        count = selectors.count_pages(window.start, window.end)
        rows = selectors.top_pages(
            window.start, window.end, limit=page_size, offset=(page - 1) * page_size
        )
        return {**_meta(window), **_paged(rows, count, page, page_size)}


class SourcesView(AnalyticsView):
    """``/sources/`` — the channel doughnut, plus the domains behind it."""

    def payload(self, request, window):
        return {
            **_meta(window),
            "channels": selectors.channels(window.start, window.end),
            "referrers": selectors.referrers(window.start, window.end),
            "labels": dict(Channel.choices),
        }


class DevicesView(AnalyticsView):
    """``/devices/`` — device, browser and operating system in one response.

    Three panels rather than three endpoints: they are always rendered together,
    each is a small grouped query, and three round trips to draw one row of the
    dashboard is latency the screen can see.
    """

    def payload(self, request, window):
        return {
            **_meta(window),
            "devices": selectors.devices(window.start, window.end),
            "browsers": selectors.browsers(window.start, window.end),
            "operating_systems": selectors.operating_systems(window.start, window.end),
            "labels": dict(Device.choices),
        }


class RealtimeView(AnalyticsView):
    """``/realtime/`` — who is here now, and the recent activity feed.

    Uncached and range-independent: "now" is not a window anyone selects, and a
    live panel that serves a cached answer is not live. It is the cheapest
    endpoint here — one indexed count and one indexed tail read — which is what
    makes it safe to poll.
    """

    cache_seconds = 0

    def get(self, request):
        page, page_size = _paging(request, default_size=25, max_size=100)
        return Response(
            {
                **selectors.live(),
                "has_data": selectors.has_any_data(),
                **_paged(
                    api_serializers.activity_payload(
                        selectors.recent_activity(
                            limit=page_size, offset=(page - 1) * page_size
                        )
                    ),
                    selectors.count_activity(),
                    page,
                    page_size,
                ),
            }
        )


class ExportView(AnalyticsView):
    """``/export/`` — the current view as CSV.

    Streamed as one response rather than assembled as a file: an export is a
    read of numbers already on screen, and writing it to disk to hand it back
    would add a cleanup problem to a request that does not need one.
    """

    cache_seconds = 0

    def get(self, request):
        try:
            window = ranges.parse(request.query_params)
        except ranges.InvalidRange as error:
            return Response({"detail": str(error)}, status=400)

        rows = api_serializers.export_rows(window)
        body = "\r\n".join(",".join(_csv_cell(cell) for cell in row) for row in rows)
        response = HttpResponse(body, content_type="text/csv; charset=utf-8")
        stamp = window.start.strftime("%Y%m%d")
        response["Content-Disposition"] = (
            f'attachment; filename="zion-analytics-{window.key}-{stamp}.csv"'
        )
        return response


def _csv_cell(value) -> str:
    text = "" if value is None else str(value)
    if any(ch in text for ch in ',"\r\n'):
        return '"' + text.replace('"', '""') + '"'
    return text


def _paging(request, *, default_size: int, max_size: int) -> tuple[int, int]:
    """``(page, page_size)`` from the query string, clamped rather than rejected.

    A nonsensical page number is a stale link or a fat finger, and answering it
    with the first page is more useful than a 400 the UI has to render.
    """
    page = _positive(request.query_params.get("page"), 1)
    size = _positive(request.query_params.get("page_size"), default_size)
    return page, min(size, max_size)


def _positive(raw, fallback: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def _paged(rows, count: int, page: int, page_size: int) -> dict:
    """The pagination envelope the panel's tables already know how to read."""
    return {
        "results": rows,
        "count": count,
        "page": page,
        "pages": max(1, -(-count // page_size)),  # ceiling division
        "page_size": page_size,
    }
