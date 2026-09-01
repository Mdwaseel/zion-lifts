"""Routes, generated from the registry.

Every registered resource gets the standard set at ``/api/admin/<key>/``:

    GET    <key>/            list, paginated, searchable, filterable
    POST   <key>/            create
    GET    <key>/<id>/       detail
    PATCH  <key>/<id>/       update
    DELETE <key>/<id>/       delete
    GET    <key>/schema/     field description, for the form renderer
    GET    <key>/options/    choices for this resource's relation fields
    POST   <key>/bulk/       publish / unpublish / delete the selected rows

Adding a model to ``resources.py`` therefore adds its routes; there is nothing
to wire up by hand and nothing to forget.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .registry import registry
from .views import (
    ActivityView,
    DashboardView,
    NavigationView,
    OperationsIngestionView,
    OperationsOverviewView,
    OperationsProvidersView,
    UploadView,
    for_resource,
)

app_name = "adminpanel"

router = DefaultRouter()
for resource in registry:
    router.register(resource.key, for_resource(resource), basename=f"admin-{resource.key}")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("navigation/", NavigationView.as_view(), name="navigation"),
    path("activity/", ActivityView.as_view(), name="activity"),
    # Media from an operator's own computer. One route for every collection —
    # the panel has one form component, so it needs one upload endpoint.
    path("uploads/", UploadView.as_view(), name="uploads"),
    # Operational health. Staff-only like everything else in this app, and
    # read-only: see the note at the top of views/operations.py.
    path(
        "operations/overview/",
        OperationsOverviewView.as_view(),
        name="operations-overview",
    ),
    path(
        "operations/ingestion/",
        OperationsIngestionView.as_view(),
        name="operations-ingestion",
    ),
    path(
        "operations/providers/",
        OperationsProvidersView.as_view(),
        name="operations-providers",
    ),
    path("", include(router.urls)),
]
