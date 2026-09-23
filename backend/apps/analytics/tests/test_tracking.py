"""The write path: what the public endpoint accepts, stores, and refuses to store."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.analytics import services
from apps.analytics.models import Channel, Device, PageView, Session, Visitor

from .base import CHROME_DESKTOP, SAFARI_IPHONE, TRACK, AnalyticsTestCase


class TrackEndpointTests(AnalyticsTestCase):
    def test_an_anonymous_visitor_can_record_a_page_view(self):
        res = self.track(path="/lifts")

        self.assertEqual(res.status_code, 202)
        view = PageView.objects.get()
        self.assertEqual(view.path, "/lifts")
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(Visitor.objects.count(), 1)

    def test_signing_in_is_not_required(self):
        """The tracker runs before anyone has an account. It must stay open."""
        self.assertEqual(self.as_anonymous().post(
            TRACK,
            {"visitor_id": str(uuid.uuid4()), "event_id": str(uuid.uuid4()), "path": "/"},
            format="json",
        ).status_code, 202)

    def test_the_same_event_id_twice_stores_one_view(self):
        """sendBeacon reports no outcome, so the browser retries what it cannot confirm."""
        event = str(uuid.uuid4())
        visitor = str(uuid.uuid4())

        self.track(visitor_id=visitor, event_id=event, path="/about")
        self.track(visitor_id=visitor, event_id=event, path="/about")

        self.assertEqual(PageView.objects.count(), 1)

    def test_a_missing_path_is_a_bad_request(self):
        res = self.as_anonymous().post(
            TRACK, {"visitor_id": str(uuid.uuid4()), "event_id": str(uuid.uuid4())}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_a_malformed_visitor_id_is_a_bad_request(self):
        res = self.as_anonymous().post(
            TRACK,
            {"visitor_id": "not-a-uuid", "event_id": str(uuid.uuid4()), "path": "/"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(PageView.objects.count(), 0)

    def test_a_crawler_is_not_counted(self):
        res = self.as_anonymous().post(
            TRACK,
            {"visitor_id": str(uuid.uuid4()), "event_id": str(uuid.uuid4()), "path": "/"},
            format="json",
            HTTP_USER_AGENT="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        )
        # Accepted rather than refused: arguing with a crawler achieves nothing,
        # and a 4xx would only make it retry.
        self.assertEqual(res.status_code, 202)
        self.assertEqual(PageView.objects.count(), 0)

    def test_a_tracking_failure_never_reaches_the_visitor(self):
        """A broken analytics table must not put an error in someone's console."""
        from unittest import mock

        with mock.patch(
            "apps.analytics.services.track", side_effect=RuntimeError("table is gone")
        ):
            res = self.track(path="/")

        self.assertEqual(res.status_code, 202)


class PathHandlingTests(AnalyticsTestCase):
    def test_a_query_string_is_dropped(self):
        """It is where identifying detail hides, and it shatters Top Pages."""
        self.track(path="/contact?utm_source=email&token=abc123")
        self.assertEqual(PageView.objects.get().path, "/contact")

    def test_a_fragment_is_dropped(self):
        self.track(path="/faq#safety")
        self.assertEqual(PageView.objects.get().path, "/faq")

    def test_a_trailing_slash_is_the_same_page(self):
        self.assertEqual(services.normalise_path("/lifts/"), "/lifts")
        self.assertEqual(services.normalise_path("/lifts"), "/lifts")

    def test_the_root_keeps_its_slash(self):
        self.assertEqual(services.normalise_path("/"), "/")

    def test_a_path_without_a_leading_slash_gains_one(self):
        self.assertEqual(services.normalise_path("about"), "/about")

    def test_an_absurdly_long_path_is_bounded(self):
        self.assertLessEqual(len(services.normalise_path("/" + "a" * 900)), 300)


class SessionWindowTests(AnalyticsTestCase):
    """A session is a run of activity, not a fixed-length window."""

    def test_two_views_close_together_are_one_visit(self):
        visitor = str(uuid.uuid4())
        self.track(visitor_id=visitor, path="/")
        self.track(visitor_id=visitor, path="/lifts")

        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(Session.objects.get().page_view_count, 2)

    def test_a_view_after_the_timeout_starts_a_new_visit(self):
        visitor_key = uuid.uuid4()
        self.track(visitor_id=str(visitor_key), path="/")

        stale = timezone.now() - timedelta(minutes=31)
        Session.objects.update(last_activity_at=stale, started_at=stale)

        self.track(visitor_id=str(visitor_key), path="/lifts")

        self.assertEqual(Session.objects.count(), 2)
        self.assertEqual(Visitor.objects.count(), 1, "the same browser is still one visitor")

    @override_settings(ANALYTICS_SESSION_TIMEOUT_MINUTES=1)
    def test_the_timeout_is_configurable(self):
        visitor_key = uuid.uuid4()
        self.track(visitor_id=str(visitor_key), path="/")
        Session.objects.update(last_activity_at=timezone.now() - timedelta(minutes=2))

        self.track(visitor_id=str(visitor_key), path="/about")
        self.assertEqual(Session.objects.count(), 2)

    def test_long_reading_without_a_gap_stays_one_visit(self):
        """Activity, not elapsed time, is what keeps a session open."""
        visitor_key = uuid.uuid4()
        self.track(visitor_id=str(visitor_key), path="/")
        for _ in range(3):
            Session.objects.update(last_activity_at=timezone.now() - timedelta(minutes=20))
            self.track(visitor_id=str(visitor_key), path="/lifts")

        self.assertEqual(Session.objects.count(), 1)

    def test_the_first_visit_is_flagged_as_such(self):
        visitor_key = uuid.uuid4()
        self.track(visitor_id=str(visitor_key), path="/")
        self.assertTrue(Session.objects.get().is_first)

        Session.objects.update(last_activity_at=timezone.now() - timedelta(hours=2))
        self.track(visitor_id=str(visitor_key), path="/")

        self.assertEqual(Session.objects.filter(is_first=True).count(), 1)


class TimeOnPageTests(AnalyticsTestCase):
    def test_the_previous_view_gets_its_duration_when_the_next_arrives(self):
        visitor = str(uuid.uuid4())
        self.track(visitor_id=visitor, path="/")
        first = PageView.objects.get()
        PageView.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(seconds=45)
        )

        self.track(visitor_id=visitor, path="/lifts")

        first.refresh_from_db()
        self.assertGreaterEqual(first.duration_seconds, 40)

    def test_the_last_view_of_a_visit_keeps_a_null_duration(self):
        """Nothing tells us how long someone spent on the page they left from."""
        self.track(path="/")
        self.assertIsNone(PageView.objects.get().duration_seconds)

    def test_an_abandoned_tab_cannot_produce_an_absurd_duration(self):
        visitor = str(uuid.uuid4())
        self.track(visitor_id=visitor, path="/")
        first = PageView.objects.get()
        PageView.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(hours=9)
        )
        # Keep the session open so the second view lands in it.
        Session.objects.update(last_activity_at=timezone.now())

        self.track(visitor_id=visitor, path="/about")

        first.refresh_from_db()
        self.assertEqual(first.duration_seconds, services.MAX_VIEW_SECONDS)


class DimensionTests(AnalyticsTestCase):
    def test_a_phone_is_recorded_as_mobile(self):
        self.as_anonymous().post(
            TRACK,
            {"visitor_id": str(uuid.uuid4()), "event_id": str(uuid.uuid4()), "path": "/"},
            format="json",
            HTTP_USER_AGENT=SAFARI_IPHONE,
        )
        session = Session.objects.get()
        self.assertEqual(session.device, Device.MOBILE)
        self.assertEqual(session.browser, "Safari")
        self.assertEqual(session.os, "iOS")

    def test_a_desktop_is_recorded_as_desktop(self):
        self.as_anonymous().post(
            TRACK,
            {"visitor_id": str(uuid.uuid4()), "event_id": str(uuid.uuid4()), "path": "/"},
            format="json",
            HTTP_USER_AGENT=CHROME_DESKTOP,
        )
        session = Session.objects.get()
        self.assertEqual(session.device, Device.DESKTOP)
        self.assertEqual(session.browser, "Chrome")
        self.assertEqual(session.os, "Windows")

    def test_a_search_referrer_is_classified_as_search(self):
        self.track(path="/", referrer="https://www.google.com/search?q=home+lift+hyderabad")
        session = Session.objects.get()
        self.assertEqual(session.channel, Channel.SEARCH)
        self.assertEqual(session.referrer_host, "google.com")

    def test_only_the_referring_host_is_kept(self):
        """The search someone typed is not ours to store."""
        self.track(path="/", referrer="https://www.google.com/search?q=something+private")
        self.assertEqual(Session.objects.get().referrer_host, "google.com")

    def test_a_social_referrer_is_classified_as_social(self):
        self.track(path="/", referrer="https://l.instagram.com/?u=zionlifts")
        self.assertEqual(Session.objects.get().channel, Channel.SOCIAL)

    def test_no_referrer_is_direct(self):
        self.track(path="/")
        self.assertEqual(Session.objects.get().channel, Channel.DIRECT)

    def test_an_internal_link_is_not_a_referral(self):
        """Otherwise the site becomes its own biggest traffic source."""
        self.track(path="/lifts", referrer="http://testserver/")
        self.assertEqual(Session.objects.get().channel, Channel.DIRECT)

    @override_settings(ANALYTICS_OWN_HOSTS=["zionlifts.com"])
    def test_a_configured_domain_is_internal_even_if_the_host_header_was_rewritten(self):
        """Any proxy with changeOrigin rewrites Host; the config still knows us.

        Without this the most common deployment shape — Django behind a proxy
        that does not pass the original Host through — files every internal
        click as a referral and puts the site at the top of its own sources
        report.
        """
        self.track(path="/lifts", referrer="https://www.zionlifts.com/projects")
        self.assertEqual(Session.objects.get().channel, Channel.DIRECT)

    @override_settings(ANALYTICS_OWN_HOSTS=["zionlifts.com"])
    def test_a_genuine_referral_still_counts_as_one(self):
        self.track(path="/lifts", referrer="https://architectsjournal.com/piece")
        session = Session.objects.get()
        self.assertEqual(session.channel, Channel.REFERRAL)
        self.assertEqual(session.referrer_host, "architectsjournal.com")

    @override_settings(ANALYTICS_OWN_HOSTS=["*"])
    def test_a_wildcard_allowed_host_does_not_swallow_every_referrer(self):
        """ALLOWED_HOSTS = ["*"] must not empty the traffic sources report."""
        self.track(path="/", referrer="https://www.google.com/search?q=lifts")
        self.assertEqual(Session.objects.get().channel, Channel.SEARCH)


class PrivacyTests(AnalyticsTestCase):
    def test_no_ip_address_or_user_agent_is_stored_anywhere(self):
        """The narrowing happens on the way in, so the raw values never land."""
        self.track(path="/")

        columns = {f.name for f in Session._meta.get_fields()}
        columns |= {f.name for f in PageView._meta.get_fields()}
        columns |= {f.name for f in Visitor._meta.get_fields()}

        for forbidden in ("ip", "ip_address", "user_agent", "remote_addr", "email", "user"):
            self.assertNotIn(forbidden, columns)

    @override_settings(
        ANALYTICS_GEO_HEADERS={
            "country": ("HTTP_CF_IPCOUNTRY",),
            "region": ("HTTP_CF_REGION",),
            "city": ("HTTP_CF_IPCITY",),
        }
    )
    def test_geography_comes_from_a_proxy_header_when_one_is_present(self):
        self.as_anonymous().post(
            TRACK,
            {"visitor_id": str(uuid.uuid4()), "event_id": str(uuid.uuid4()), "path": "/"},
            format="json",
            HTTP_USER_AGENT=CHROME_DESKTOP,
            HTTP_CF_IPCOUNTRY="IN",
            HTTP_CF_IPCITY="Hyderabad",
        )
        session = Session.objects.get()
        self.assertEqual(session.country, "India")
        self.assertEqual(session.city, "Hyderabad")

    def test_without_a_proxy_header_location_is_simply_empty(self):
        """No lookup, no guess — an empty column rather than an invented one."""
        self.track(path="/")
        session = Session.objects.get()
        self.assertEqual(session.country, "")
        self.assertEqual(session.city, "")
