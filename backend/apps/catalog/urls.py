from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApplicationViewSet,
    ComponentViewSet,
    FinishOptionViewSet,
    LiftTypeViewSet,
    SafetyFeatureViewSet,
)

router = DefaultRouter()
router.register("lifts", LiftTypeViewSet)
router.register("applications", ApplicationViewSet)
router.register("safety-features", SafetyFeatureViewSet)
router.register("finishes", FinishOptionViewSet)
router.register("components", ComponentViewSet)

urlpatterns = [path("", include(router.urls))]
