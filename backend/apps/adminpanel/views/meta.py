"""Endpoints describing the panel itself, rather than any one collection."""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserSerializer

from .. import audit
from ..permissions import IsAdminPanelUser
from ..registry import registry
from ..schema import describe_resource

ACTIVITY_ROWS = 50


class NavigationView(APIView):
    """Everything the shell needs on first paint: who you are, and the sidebar.

    Descriptions here are the trimmed kind — the sidebar needs labels and
    permissions, not every field of every collection. A screen fetches its own
    resource's full schema when it opens.
    """

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        return Response(
            {
                "user": UserSerializer(request.user).data,
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


class ActivityView(APIView):
    """The full audit trail, newest first."""

    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        return Response({"results": audit.recent(ACTIVITY_ROWS)})
