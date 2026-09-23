"""The landing screen: what needs attention, and what changed recently."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import audit
from ..models import Enquiry, ServiceRequest
from ..permissions import IsAdminPanelUser
from ..registry import registry

RECENT_DAYS = 30
RECENT_ROWS = 8


class DashboardView(APIView):
    """One request, one screen.

    Assembled server-side rather than letting the client fan out across a dozen
    list endpoints: it is a handful of aggregate queries here versus a dozen
    round trips and a dozen paginated payloads there.
    """

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        since = timezone.now() - timedelta(days=RECENT_DAYS)
        return Response(
            {
                "inbox": {
                    "enquiries": _pipeline(Enquiry, since),
                    "service_requests": _pipeline(ServiceRequest, since),
                },
                "urgent": _urgent(),
                "recent_enquiries": _recent_enquiries(),
                "collections": _collection_counts(),
                "activity": audit.recent(RECENT_ROWS),
                "window_days": RECENT_DAYS,
            }
        )


def _pipeline(model, since) -> dict:
    """Totals and a per-status breakdown, in the model's own choice order."""
    counts = dict(
        model.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n")
    )
    statuses = [
        {"value": value, "label": str(label), "count": counts.get(value, 0)}
        for value, label in model._meta.get_field("status").choices
    ]
    return {
        "total": sum(counts.values()),
        "recent": model.objects.filter(created_at__gte=since).count(),
        # "new" is the default status every submission lands in, so this is the
        # number the dashboard leads with: work not yet picked up.
        "unhandled": counts.get("new", 0),
        "statuses": statuses,
    }


def _urgent() -> list[dict]:
    """Open service requests that are not routine, oldest first."""
    rows = (
        ServiceRequest.objects.exclude(status__in=("closed", "resolved"))
        .exclude(urgency="routine")
        .order_by("created_at")[:RECENT_ROWS]
    )
    return [
        {
            "id": row.pk,
            "name": row.name,
            "site": row.site_name or row.location or "—",
            "kind": row.get_kind_display(),
            "urgency": row.get_urgency_display(),
            "status": row.get_status_display(),
            "created_at": row.created_at,
        }
        for row in rows
    ]


def _recent_enquiries() -> list[dict]:
    rows = Enquiry.objects.select_related("lift").order_by("-created_at")[:RECENT_ROWS]
    return [
        {
            "id": row.pk,
            "name": row.name,
            "location": row.location or "—",
            "lift_type": str(row.lift) if row.lift else (row.lift_type_note or "—"),
            "status": row.get_status_display(),
            "created_at": row.created_at,
        }
        for row in rows
    ]


def _collection_counts() -> list[dict]:
    """Row counts per registered collection, with unpublished flagged.

    Unpublished is the number worth seeing: it is usually work in progress that
    someone forgot to turn on, and the panel links straight to that filter.

    Twenty-nine tables cannot be counted in one query, but each one can be
    counted once instead of twice — a conditional aggregate gets the total and
    the unpublished subset in a single pass, which is what keeps the landing
    screen at roughly one query per collection rather than two.
    """
    summary = []
    for resource in registry:
        if resource.singleton:
            continue

        publishable = resource.has_field("is_published")
        aggregates = {"total": Count("pk")}
        if publishable:
            aggregates["unpublished"] = Count("pk", filter=Q(is_published=False))
        totals = resource.model._default_manager.aggregate(**aggregates)

        summary.append(
            {
                "key": resource.key,
                "label": resource.label_plural,
                "group": resource.group,
                "icon": resource.icon,
                "count": totals["total"],
                # None, not 0: "not applicable" and "nothing to publish" are
                # different answers and the UI renders them differently.
                "unpublished": totals["unpublished"] if publishable else None,
            }
        )
    return summary
