"""Endpoints describing the panel itself, rather than any one collection."""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserSerializer

from .. import audit, notifications
from ..permissions import IsAdminPanelUser
from ..registry import registry
from ..schema import describe_resource

ACTIVITY_ROWS = 50


class NavigationView(APIView):
    """Everything the shell needs on first paint: who you are, and the sidebar.

    Descriptions here are the trimmed kind — the sidebar needs labels and
    permissions, not every field of every collection. A screen fetches its own
    resource's full schema when it opens.

    The unread counts ride along so the badges are right on the first paint
    rather than appearing a poll later. They are refreshed after that from
    ``/notifications/``, which is the same numbers without the sidebar around
    them.
    """

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "notifications": notifications.summary(),
                "groups": [
                    {
                        "group": entry["group"],
                        "resources": [
                            describe_resource(r, detail=False) for r in entry["resources"]
                        ],
                    }
                    for entry in registry.grouped()
                ],
            }
        )


class NotificationsView(APIView):
    """``/notifications/`` — how much has arrived that nobody has opened.

    Its own endpoint because the sidebar polls it. Re-fetching the whole
    navigation payload every half minute to refresh two integers would re-send
    every label, permission and tab in the panel, none of which changes between
    one poll and the next.
    """

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        return Response(notifications.summary())


class ActivityView(APIView):
    """The full audit trail, newest first."""

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        return Response({"results": audit.recent(ACTIVITY_ROWS)})
