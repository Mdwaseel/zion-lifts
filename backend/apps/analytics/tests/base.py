"""Shared fixtures for the analytics tests.

The helpers here write history directly rather than through the tracking
endpoint. That is deliberate: the endpoint's job is tested on its own, and the
selectors need traffic at chosen timestamps — a week ago, three minutes ago —
which a POST can only ever place at "now".
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import Channel, Device, PageView, Session, Visitor

User = get_user_model()

ADMIN = "/api/admin/analytics"
TRACK = "/api/analytics/track/"

CHROME_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AnalyticsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="control", email="control@zionlifts.test",
            password="an-ordinary-long-passphrase-42", is_staff=True,
        )
        cls.plain = User.objects.create_user(
            username="visitor", email="visitor@zionlifts.test",
            password="an-ordinary-long-passphrase-42",
        )

    def setUp(self):
        # The admin endpoints cache for a minute; without this, the second test
        # to ask for the same window would assert against the first one's data.
        cache.clear()
        logging.disable(logging.CRITICAL)
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def tearDown(self):
        logging.disable(logging.NOTSET)
        cache.clear()

    def as_anonymous(self) -> APIClient:
        return APIClient()

    def as_non_staff(self) -> APIClient:
        client = APIClient()
        client.force_authenticate(self.plain)
        return client

    def get(self, endpoint, expect=200, **params):
        # `endpoint`, not `path`: ``path`` is itself a query parameter on the
        # pages report, and naming the positional the same thing makes
        # ``self.get("/pages/", path="/lifts")`` a TypeError rather than a test.
        res = self.client.get(f"{ADMIN}{endpoint}", params)
        self.assertEqual(
            res.status_code, expect, f"GET {endpoint} -> {res.status_code} {res.content[:300]}"
        )
        return res.json() if res.content else {}

    # --- building history -------------------------------------------------
    def visit(
        self,
        *paths,
        visitor: Visitor | None = None,
        at=None,
        gap_seconds: int = 30,
        device=Device.DESKTOP,
        browser="Chrome",
        os="Windows",
        channel=Channel.DIRECT,
        country="",
        city="",
    ) -> Session:
        """One visit that viewed ``paths`` in order, ``gap_seconds`` apart.

        Returns the session. Durations are filled in the way the live tracker
        fills them — every view but the last — so tests of "average time on
        page" exercise the same null handling production does.
        """
        moment = at or timezone.now()
        visitor = visitor or self.visitor(first_seen=moment)

        session = Session.objects.create(
            visitor=visitor, started_at=moment, last_activity_at=moment,
            page_view_count=len(paths), is_first=visitor.sessions.count() == 0,
            device=device, browser=browser, os=os, channel=channel,
            country=country, city=city,
            entry_path=paths[0], exit_path=paths[-1],
        )

        at_view = moment
        for index, path in enumerate(paths):
            PageView.objects.create(
                event_key=uuid.uuid4(), visitor=visitor, session=session, path=path,
                created_at=at_view,
                duration_seconds=None if index == len(paths) - 1 else gap_seconds,
            )
            at_view += timedelta(seconds=gap_seconds)

        session.last_activity_at = at_view - timedelta(seconds=gap_seconds)
        session.save(update_fields=["last_activity_at"])
        Visitor.objects.filter(pk=visitor.pk).update(
            last_seen=session.last_activity_at,
            session_count=visitor.sessions.count(),
            page_view_count=visitor.page_views.count(),
        )
        return session

    def visitor(self, *, first_seen=None) -> Visitor:
        moment = first_seen or timezone.now()
        return Visitor.objects.create(
            key=uuid.uuid4(), first_seen=moment, last_seen=moment
        )

    def track(self, client=None, **body):
        """POST one page view through the real endpoint."""
        payload = {
            "visitor_id": str(uuid.uuid4()),
            "event_id": str(uuid.uuid4()),
            "path": "/",
            **body,
        }
        return (client or self.as_anonymous()).post(
            TRACK, payload, format="json", HTTP_USER_AGENT=CHROME_DESKTOP
        )
