"""Admin analytics routes, mounted at ``/api/admin/analytics/``.

Plain paths rather than a router: none of these is a collection with a detail
view, so a ViewSet would be inventing REST semantics for what are eight
purpose-built reports. Every one is staff-gated by ``AnalyticsView``.
"""

from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("overview/", views.OverviewView.as_view(), name="overview"),
    path("visitors/", views.VisitorsView.as_view(), name="visitors"),
    path("pages/", views.PagesView.as_view(), name="pages"),
    path("sources/", views.SourcesView.as_view(), name="sources"),
    path("devices/", views.DevicesView.as_view(), name="devices"),
    path("realtime/", views.RealtimeView.as_view(), name="realtime"),
    path("export/", views.ExportView.as_view(), name="export"),
]
