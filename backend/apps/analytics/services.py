"""The write path: turning one tracking request into one page view.

This is the only code in the project that runs on behalf of every visitor to
every page, so its cost is the site's cost. The whole operation is a bounded
handful of indexed statements — no counting, no aggregation, nothing that grows
with how much history the visitor or the site has:

    1. find-or-create the visitor            (unique index on key)
    2. find the live session, or open one    (index on visitor, -last_activity_at)
    3. close out the previous view's duration
    4. insert the page view                  (unique index on event_key)
    5. bump the counters

Aggregation happens when somebody opens the dashboard, which is a handful of
times a day, rather than on every page view, which is continuous. That is the
central trade in this app and everything else follows from it.

Nothing here is allowed to break a page. :func:`track` raises only for input the
caller should reject with a 400; the view wraps the rest, and a tracking failure
is logged and swallowed. An analytics table is never worth an error page.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from . import geo, sources, useragent
from .models import PageView, Session, Visitor, session_timeout_minutes

log = logging.getLogger(__name__)

MAX_PATH = 300

# A single view cannot contribute more than this to "time on page". Without a
# cap, the tab someone left open over a long weekend becomes a 62-hour visit and
# drags every average on the dashboard with it.
MAX_VIEW_SECONDS = 30 * 60


class TrackingRejected(ValueError):
    """The payload was unusable. The caller turns this into a 400."""


def normalise_path(raw: str | None) -> str:
    """The path we store: leading slash, no query string, no fragment, bounded.

    The query string goes because it is where identifying detail hides — an
    email campaign's ``?token=``, a form's echoed input — and because keeping it
    would shatter one page into a thousand rows in Top Pages. A trailing slash
    is trimmed so ``/lifts`` and ``/lifts/`` are one page rather than two.
    """
    path = (raw or "").strip()
    if not path:
        raise TrackingRejected("A path is required.")
    path = path.split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    return path[:MAX_PATH]


def _uuid(value, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise TrackingRejected(f"{field} must be a UUID.") from None


@transaction.atomic
def track(
    *,
    visitor_key,
    event_key,
    path: str,
    referrer: str | None,
    user_agent: str | None,
    request,
) -> PageView | None:
    """Record one page view. Returns ``None`` if it was a duplicate.

    A duplicate is not an error: ``sendBeacon`` reports no outcome, so the
    browser retries what it cannot confirm, and the second delivery of a view
    already stored is the system working. The unique constraint on ``event_key``
    is what makes that safe, and it is enforced by the database rather than by a
    read-then-write, which two concurrent retries would race straight through.
    """
    if useragent.is_bot(user_agent):
        return None

    visitor_uuid = _uuid(visitor_key, "visitor_id")
    event_uuid = _uuid(event_key, "event_id")
    stored_path = normalise_path(path)
    now = timezone.now()

    visitor, created = Visitor.objects.get_or_create(
        key=visitor_uuid,
        defaults={"first_seen": now, "last_seen": now},
    )

    session, opened = _live_session(
        visitor=visitor,
        created_visitor=created,
        now=now,
        path=stored_path,
        referrer=referrer,
        user_agent=user_agent,
        request=request,
    )

    try:
        with transaction.atomic():  # savepoint: a duplicate must not poison the outer txn
            view = PageView.objects.create(
                event_key=event_uuid,
                visitor=visitor,
                session=session,
                path=stored_path,
                referrer_host=sources.referrer_host(referrer),
                created_at=now,
            )
    except IntegrityError:
        # Already stored. If this retry also opened a session, that session is
        # real — the visitor was active — so it stays; it simply has no view yet
        # and will pick up the next one.
        if opened:
            log.debug("duplicate page view opened a session | visitor=%s", visitor_uuid)
        return None

    _close_previous_view(session, before=view, now=now)

    Session.objects.filter(pk=session.pk).update(
        last_activity_at=now,
        exit_path=stored_path,
        page_view_count=session.page_view_count + 1,
    )
    Visitor.objects.filter(pk=visitor.pk).update(
        last_seen=now,
        page_view_count=visitor.page_view_count + 1,
    )
    return view


def _live_session(
    *, visitor, created_visitor, now, path, referrer, user_agent, request
) -> tuple[Session, bool]:
    """The visitor's open session, or a new one. Returns ``(session, opened)``.

    "Open" means touched within the timeout. The check is on ``last_activity_at``
    rather than on ``started_at``, which is what makes a session a run of
    activity rather than a fixed-length window: somebody reading for two hours
    without a thirty-minute gap is one visit, correctly.
    """
    cutoff = now - timedelta(minutes=session_timeout_minutes())

    if not created_visitor:
        live = (
            Session.objects.filter(visitor=visitor, last_activity_at__gte=cutoff)
            .order_by("-last_activity_at")
            .first()
        )
        if live is not None:
            return live, False

    device, browser, os_name = useragent.classify(user_agent)
    channel, host = sources.classify(referrer, own_hosts=_own_hosts(request))
    location = geo.resolve(request)

    session = Session.objects.create(
        visitor=visitor,
        started_at=now,
        last_activity_at=now,
        is_first=created_visitor,
        device=device,
        browser=browser,
        os=os_name,
        channel=channel,
        referrer_host=host,
        country=location["country"],
        region=location["region"],
        city=location["city"],
        entry_path=path,
        exit_path=path,
    )
    Visitor.objects.filter(pk=visitor.pk).update(session_count=visitor.session_count + 1)
    return session, True


def _close_previous_view(session: Session, *, before: PageView, now) -> None:
    """Give the view before this one its time-on-page.

    Time on a page is only knowable once the reader leaves it, and the only
    reliable signal that they left is the arrival of the next page. That is why
    this runs on the *next* view rather than on a beforeunload handler, which
    fires unreliably on mobile and not at all when a tab is killed.
    """
    previous = (
        PageView.objects.filter(session=session, created_at__lte=now)
        .exclude(pk=before.pk)
        .order_by("-created_at")
        .first()
    )
    if previous is None or previous.duration_seconds is not None:
        return

    seconds = int((now - previous.created_at).total_seconds())
    PageView.objects.filter(pk=previous.pk).update(
        duration_seconds=max(0, min(seconds, MAX_VIEW_SECONDS))
    )


def _own_hosts(request) -> tuple[str, ...]:
    """This site's own domains, so an internal link is not counted as a referral.

    Two sources, unioned, because neither is sufficient alone:

    * ``ALLOWED_HOSTS`` (overridable with ``ANALYTICS_OWN_HOSTS``) is the list of
      names this site answers on, and it is right even when the request's Host
      header has been rewritten — which any proxy configured with something like
      Vite's ``changeOrigin`` does. Relying on the request alone means a visitor
      clicking from one page of the site to another is filed under Referral,
      with the site as its own top traffic source.
    * the request's host covers the deployment nobody remembered to configure,
      and any domain added after ``ALLOWED_HOSTS`` was last edited.

    A wildcard entry is dropped: ``ALLOWED_HOSTS = ["*"]`` would otherwise make
    every referrer internal and empty the sources report entirely.
    """
    configured = getattr(settings, "ANALYTICS_OWN_HOSTS", None)
    if configured is None:
        configured = settings.ALLOWED_HOSTS

    hosts = {_bare(host) for host in configured}
    try:
        hosts.add(_bare(request.get_host()))
    except Exception:  # DisallowedHost — not this code's problem to resolve
        pass

    return tuple(host for host in hosts if host and "*" not in host)


def _bare(host: str) -> str:
    """A host with its port and leading ``www.`` removed, lowercased."""
    bare = str(host).split(":")[0].strip().lower().lstrip(".")
    return bare[4:] if bare.startswith("www.") else bare
