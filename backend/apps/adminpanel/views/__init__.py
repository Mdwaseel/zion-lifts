"""View layer, split by what each family of endpoints is for."""

from .base import AdminResourceViewSet, SingletonAdminViewSet, for_resource
from .dashboard import DashboardView
from .meta import ActivityView, NavigationView
from .operations import (
    OperationsIngestionView,
    OperationsOverviewView,
    OperationsProvidersView,
)

__all__ = [
    "AdminResourceViewSet",
    "SingletonAdminViewSet",
    "for_resource",
    "DashboardView",
    "ActivityView",
    "NavigationView",
    "OperationsOverviewView",
    "OperationsIngestionView",
    "OperationsProvidersView",
]
