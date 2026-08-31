from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CertificationViewSet,
    OfficeViewSet,
    PartnerViewSet,
    SiteSettingsView,
    StatViewSet,
)

router = DefaultRouter()
router.register("offices", OfficeViewSet)
router.register("stats", StatViewSet)
router.register("partners", PartnerViewSet)
router.register("certifications", CertificationViewSet)

urlpatterns = [
    path("site/", SiteSettingsView.as_view(), name="site-settings"),
    path("", include(router.urls)),
]
