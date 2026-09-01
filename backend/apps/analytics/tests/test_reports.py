"""The read path: the admin endpoints, their arithmetic, and who may call them."""

from __future__ import annotations

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.analytics import ranges, selectors
from apps.analytics.api import serializers
from apps.analytics.models import Channel, Device, PageView, Session, Visitor

from .base import ADMIN, AnalyticsTestCase

ENDPOINTS = (
    "/overview/", "/visitors/", "/pages/", "/sources/", "/devices/", "/realtime/",
)


class AuthorisationTests(AnalyticsTestCase):
    def test_every_report_refuses_an_anonymous_caller(self):
        for path in ENDPOINTS:
            with self.subTest(endpoint=path):
                self.assertEqual(self.as_anonymous().get(f"{ADMIN}{path}").status_code, 401)

    def test_every_report_refuses_a_signed_in_non_staff_user(self):
        """Having an account is not the same as being allowed to read this."""
        for path in ENDPOINTS:
            with self.subTest(endpoint=path):
                self.assertEqual(self.as_non_staff().get(f"{ADMIN}{path}").status_code, 403)

    def test_the_export_is_gated_too(self):
        self.assertEqual(self.as_anonymous().get(f"{ADMIN}/export/").status_code, 401)
        self.assertEqual(self.as_non_staff().get(f"{ADMIN}/export/").status_code, 403)


class OverviewTests(AnalyticsTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        # Two visitors today, one of whom came twice; one visitor last week.
        returning = self.visitor(first_seen=now - timedelta(days=20))
        self.visit("/", "/lifts", at=now - timedelta(hours=2), visitor=returning)
        self.visit("/about", at=now - timedelta(hours=1), visitor=returning)
        self.visit("/", at=now - timedelta(hours=3))
        self.visit("/contact", at=now - timedelta(days=5))

    def test_unique_visitors_counts_people_not_visits(self):
        body = self.get("/overview/", range="today")
        cards = {card["key"]: card for card in body["cards"]}

        self.assertEqual(cards["visitors"]["value"], 2)
        self.assertEqual(body["traffic"]["sessions"], 3)

    def test_page_views_counts_pages(self):
        body = self.get("/overview/", range="today")
        cards = {card["key"]: card for card in body["cards"]}
        self.assertEqual(cards["page_views"]["value"], 4)

    def test_new_and_returning_split_by_when_the_visitor_first_arrived(self):
        traffic = self.get("/overview/", range="today")["traffic"]
        self.assertEqual(traffic["new_visitors"], 1)
        self.assertEqual(traffic["returning_visitors"], 1)

    def test_every_card_the_dashboard_expects_is_present(self):
        keys = {card["key"] for card in self.get("/overview/", range="7d")["cards"]}
        self.assertEqual(
            keys,
            {
                "visitors", "page_views", "visitors_today", "page_views_today",
                "visitors_week", "visitors_month", "online", "avg_session",
            },
        )

    def test_a_change_against_an_empty_previous_period_is_null_not_a_triumph(self):
        """There is no percentage change from nothing, and inventing one lies."""
        self.assertIsNone(selectors.change(current=40, previous=0))
        self.assertEqual(selectors.change(current=110, previous=100), 10.0)
        self.assertEqual(selectors.change(current=90, previous=100), -10.0)

    def test_the_bounce_rate_is_the_share_of_single_page_visits(self):
        # Three visits above see one page; one sees two.
        traffic = self.get("/overview/", range="today")["traffic"]
        self.assertEqual(traffic["bounce_rate"], round(2 * 100 / 3, 1))


class TimeseriesTests(AnalyticsTestCase):
    def test_granularity_follows_the_span(self):
        self.assertEqual(ranges.parse({"range": "today"}).granularity, "hour")
        self.assertEqual(ranges.parse({"range": "7d"}).granularity, "day")
        self.assertEqual(ranges.parse({"range": "30d"}).granularity, "day")
        self.assertEqual(ranges.parse({"range": "12m"}).granularity, "month")

    def test_a_seven_day_range_returns_seven_daily_buckets(self):
        body = self.get("/visitors/", range="7d")
        self.assertEqual(body["granularity"], "day")
        self.assertEqual(len(body["series"]), 7)

    def test_quiet_days_appear_as_zero_rather_than_being_omitted(self):
        """A chart that drops empty buckets draws Monday next to Saturday."""
        self.visit("/", at=timezone.now() - timedelta(days=6))
        series = self.get("/visitors/", range="7d")["series"]

        self.assertEqual(len(series), 7)
        self.assertEqual(sum(point["visitors"] for point in series), 1)
        self.assertTrue(any(point["visitors"] == 0 for point in series))

    def test_every_point_carries_the_label_its_axis_prints(self):
        point = self.get("/visitors/", range="7d")["series"][0]
        self.assertTrue(point["label"])
        self.assertTrue(point["full_label"])

    def test_a_custom_range_is_accepted(self):
        today = timezone.localdate()
        body = self.get(
            "/visitors/",
            range="custom",
            start=(today - timedelta(days=3)).isoformat(),
            end=today.isoformat(),
        )
        self.assertEqual(len(body["series"]), 4)

    def test_a_malformed_custom_range_is_a_bad_request(self):
        self.get("/visitors/", expect=400, range="custom", start="not-a-date", end="2026-01-01")

    def test_an_unknown_preset_falls_back_instead_of_erroring(self):
        """A stale bookmark should show a dashboard, not a stack trace."""
        body = self.get("/visitors/", range="last-tuesday")
        self.assertEqual(body["range"]["key"], "7d")


class TopPagesTests(AnalyticsTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        for _ in range(3):
            self.visit("/", "/lifts", at=now - timedelta(hours=1), gap_seconds=60)
        self.visit("/about", at=now - timedelta(hours=1))

    def test_pages_are_ranked_by_views(self):
        rows = self.get("/pages/", range="today")["results"]
        self.assertEqual(rows[0]["path"], "/")
        self.assertEqual(rows[0]["views"], 3)

    def test_a_page_reports_its_own_unique_visitors(self):
        rows = {row["path"]: row for row in self.get("/pages/", range="today")["results"]}
        self.assertEqual(rows["/"]["visitors"], 3)

    def test_average_time_ignores_the_unknown_last_view(self):
        """Averaging a null in as zero would drag every number down."""
        rows = {row["path"]: row for row in self.get("/pages/", range="today")["results"]}
        self.assertEqual(rows["/"]["avg_seconds"], 60)
        # /lifts is only ever the last page of its visit, so nothing is known.
        self.assertEqual(rows["/lifts"]["avg_seconds"], 0)

    def test_bounce_rate_is_measured_on_the_page_people_landed_on(self):
        rows = {row["path"]: row for row in self.get("/pages/", range="today")["results"]}
        self.assertEqual(rows["/"]["bounce_rate"], 0.0)      # 3 landings, none bounced
        self.assertEqual(rows["/about"]["bounce_rate"], 100.0)  # 1 landing, bounced

    def test_the_table_is_paginated(self):
        body = self.get("/pages/", range="today", page_size=2)
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["count"], 3)
        self.assertEqual(body["pages"], 2)

    def test_a_nonsense_page_number_shows_the_first_page(self):
        body = self.get("/pages/", range="today", page="-4")
        self.assertEqual(body["page"], 1)

    def test_one_page_can_be_drilled_into(self):
        body = self.get("/pages/", range="today", path="/lifts")
        detail = body["detail"]

        self.assertEqual(detail["path"], "/lifts")
        self.assertEqual(detail["views"], 3)
        self.assertTrue(detail["series"])
        self.assertEqual(detail["next_pages"][0]["path"], "/")


class DimensionReportTests(AnalyticsTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        self.visit("/", at=now, device=Device.MOBILE, browser="Safari", os="iOS",
                   channel=Channel.SEARCH, country="India", city="Hyderabad")
        self.visit("/", at=now, device=Device.MOBILE, browser="Chrome", os="Android",
                   channel=Channel.SOCIAL, country="India", city="Mumbai")
        self.visit("/", at=now, device=Device.DESKTOP, browser="Chrome", os="Windows",
                   channel=Channel.DIRECT, country="United States", city="Austin")

    def test_devices_are_reported_with_percentages(self):
        rows = {row["key"]: row for row in self.get("/devices/", range="today")["devices"]}
        self.assertEqual(rows["mobile"]["visitors"], 2)
        self.assertEqual(rows["mobile"]["percentage"], 66.7)
        self.assertEqual(rows["desktop"]["percentage"], 33.3)

    def test_browsers_and_operating_systems_come_back_together(self):
        body = self.get("/devices/", range="today")
        self.assertEqual({row["label"] for row in body["browsers"]}, {"Chrome", "Safari"})
        self.assertEqual(
            {row["label"] for row in body["operating_systems"]}, {"iOS", "Android", "Windows"}
        )

    def test_traffic_sources_are_reported_by_channel(self):
        rows = {row["key"]: row["visitors"] for row in self.get("/sources/", range="today")["channels"]}
        self.assertEqual(rows["search"], 1)
        self.assertEqual(rows["social"], 1)
        self.assertEqual(rows["direct"], 1)

    def test_percentages_across_a_breakdown_sum_to_a_hundred(self):
        for panel in ("devices", "browsers", "operating_systems"):
            with self.subTest(panel=panel):
                rows = self.get("/devices/", range="today")[panel]
                self.assertAlmostEqual(sum(row["percentage"] for row in rows), 100.0, places=0)


class RealtimeTests(AnalyticsTestCase):
    def test_online_counts_visitors_active_in_the_window(self):
        self.visit("/", at=timezone.now() - timedelta(minutes=1))
        self.visit("/lifts", at=timezone.now() - timedelta(hours=3))

        body = self.get("/realtime/")
        self.assertEqual(body["online"], 1)

    def test_the_activity_feed_is_newest_first(self):
        self.visit("/first", at=timezone.now() - timedelta(minutes=9))
        self.visit("/second", at=timezone.now() - timedelta(minutes=1))

        rows = self.get("/realtime/")["results"]
        self.assertEqual(rows[0]["path"], "/second")

    def test_the_feed_never_exposes_who_the_visitor_is(self):
        """This panel gets read over someone's shoulder."""
        self.visit("/", at=timezone.now(), country="India", city="Hyderabad")
        row = self.get("/realtime/")["results"][0]

        self.assertEqual(set(row) & {"visitor_id", "visitor_key", "ip", "user_agent"}, set())
        self.assertEqual(row["location"], "Hyderabad, India")

    def test_the_feed_is_paginated(self):
        for index in range(5):
            self.visit(f"/page-{index}", at=timezone.now() - timedelta(minutes=index))

        body = self.get("/realtime/", page_size=2)
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["count"], 5)


class EmptyStateTests(AnalyticsTestCase):
    def test_with_no_traffic_the_reports_answer_zero_rather_than_failing(self):
        for path in ENDPOINTS:
            with self.subTest(endpoint=path):
                body = self.get(path, range="30d")
                self.assertFalse(body["has_data"])

    def test_totals_over_an_empty_window_are_zero(self):
        window = ranges.parse({"range": "30d"})
        totals = selectors.totals(window.start, window.end)

        self.assertEqual(totals["visitors"], 0)
        self.assertEqual(totals["bounce_rate"], 0.0)
        self.assertEqual(totals["avg_session_seconds"], 0)


class RealDataOnlyTests(AnalyticsTestCase):
    """The dashboard counts real visits and nothing else.

    These are the tests that would fail if a seeder, a fixture or a fallback
    number ever came back. They assert the *absence* of things, which is unusual
    but is exactly the guarantee being made: there is no code path that puts a
    row into these tables except a real visitor's beacon.
    """

    def test_there_is_no_seeder_command(self):
        from django.core.management import call_command, get_commands

        self.assertNotIn("seed_analytics", get_commands())
        with self.assertRaises(Exception):
            call_command("seed_analytics")

    def test_no_model_carries_a_demo_flag(self):
        """The column that once separated seeded rows is gone, with the rows."""
        for model in (PageView, Session, Visitor):
            with self.subTest(model=model.__name__):
                names = {f.name for f in model._meta.get_fields()}
                self.assertNotIn("is_demo", names)
                self.assertFalse(
                    names & {"is_seed", "is_fake", "is_sample", "is_test"},
                    "nothing may mark a row as synthetic, because none can be",
                )

    def test_the_api_no_longer_advertises_demo_data(self):
        self.visit("/", at=timezone.now())
        body = self.get("/overview/", range="today")

        self.assertNotIn("is_demo_data", body)

    def test_every_number_comes_from_the_rows_that_exist(self):
        """Three visits, four views: the cards say three and four.

        Placed an hour back, not at `now`: a range ending "today" is clamped to
        the current instant, and this helper spaces a multi-page visit forwards,
        so a visit started exactly now would put its second page in the future
        and outside the window.
        """
        now = timezone.now() - timedelta(hours=1)
        self.visit("/", "/lifts", at=now)
        self.visit("/", at=now)
        self.visit("/about", at=now)

        cards = {c["key"]: c["value"] for c in self.get("/overview/", range="today")["cards"]}
        self.assertEqual(cards["visitors"], 3)
        self.assertEqual(cards["page_views"], 4)
        self.assertEqual(cards["visitors_today"], 3)
        self.assertEqual(cards["page_views_today"], 4)

        self.assertEqual(PageView.objects.count(), 4)
        self.assertEqual(Visitor.objects.count(), 3)


class EmptyDatabaseTests(AnalyticsTestCase):
    """With no visitors, every number is zero — never a placeholder.

    The failure this guards against is the one that makes a dashboard useless:
    an empty table rendering as a plausible figure, with nothing on screen to
    say which it is.
    """

    def test_every_card_reads_zero(self):
        body = self.get("/overview/", range="30d")
        cards = {c["key"]: c for c in body["cards"]}

        for key in (
            "visitors", "page_views", "visitors_today", "page_views_today",
            "visitors_week", "visitors_month", "online", "avg_session",
        ):
            with self.subTest(card=key):
                self.assertEqual(cards[key]["value"], 0)

    def test_the_response_says_there_is_no_data_so_the_ui_can_explain(self):
        self.assertFalse(self.get("/overview/", range="30d")["has_data"])

    def test_online_now_is_zero_rather_than_a_random_number(self):
        body = self.get("/realtime/")
        self.assertEqual(body["online"], 0)
        self.assertEqual(body["results"], [])

    def test_online_now_becomes_one_when_one_real_visitor_is_active(self):
        self.visit("/", at=timezone.now())
        self.assertEqual(self.get("/realtime/")["online"], 1)

    def test_the_tables_are_empty_rather_than_populated_with_examples(self):
        self.assertEqual(self.get("/pages/", range="30d")["results"], [])

    def test_breakdowns_are_empty_rather_than_showing_default_percentages(self):
        devices = self.get("/devices/", range="30d")
        self.assertEqual(devices["devices"], [])
        self.assertEqual(devices["browsers"], [])
        self.assertEqual(devices["operating_systems"], [])
        self.assertEqual(self.get("/sources/", range="30d")["channels"], [])

    def test_the_chart_is_zeroes_across_the_window_not_a_shape(self):
        series = self.get("/visitors/", range="7d")["series"]

        self.assertEqual(len(series), 7, "the axis still spans the window")
        self.assertTrue(all(p["visitors"] == 0 and p["page_views"] == 0 for p in series))

    def test_percentage_change_is_null_rather_than_invented(self):
        cards = {c["key"]: c for c in self.get("/overview/", range="7d")["cards"]}
        self.assertIsNone(cards["visitors"]["change"])


class FormattingTests(AnalyticsTestCase):
    def test_durations_read_the_way_the_cards_print_them(self):
        self.assertEqual(serializers.duration(0), "0s")
        self.assertEqual(serializers.duration(42), "42s")
        self.assertEqual(serializers.duration(222), "3m 42s")
        self.assertEqual(serializers.duration(3900), "1h 5m")
        self.assertEqual(serializers.duration(None), "0s")


class ExportTests(AnalyticsTestCase):
    def test_the_export_is_a_csv_attachment(self):
        self.visit("/", "/lifts", at=timezone.now())
        res = self.client.get(f"{ADMIN}/export/", {"range": "today"})

        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn("attachment;", res["Content-Disposition"])

    def test_the_export_contains_the_numbers_on_screen(self):
        self.visit("/lifts", at=timezone.now())
        body = self.client.get(f"{ADMIN}/export/", {"range": "today"}).content.decode()

        self.assertIn("Unique visitors", body)
        self.assertIn("/lifts", body)

    def test_a_value_containing_a_comma_is_quoted(self):
        self.visit("/", at=timezone.now(), country="India", city="Hyderabad")
        body = self.client.get(f"{ADMIN}/export/", {"range": "today"}).content.decode()
        self.assertIn("Zion Lifts", body)
