from rest_framework import viewsets

from apps.core.views import PublishedViewSet

from .models import Application, Component, FinishOption, LiftType, SafetyFeature
from .serializers import (
    ApplicationSerializer,
    ComponentSerializer,
    FinishOptionSerializer,
    LiftTypeDetailSerializer,
    LiftTypeListSerializer,
    SafetyFeatureSerializer,
)


class LiftTypeViewSet(PublishedViewSet):
    queryset = LiftType.objects.prefetch_related(
        "applications", "images", "variants", "specs", "safety_features"
    )
    lookup_field = "slug"
    search_fields = ["name", "tagline", "summary"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return LiftTypeDetailSerializer
        return LiftTypeListSerializer


class ApplicationViewSet(PublishedViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    lookup_field = "slug"
    filterset_fields = ["group"]


class SafetyFeatureViewSet(PublishedViewSet):
    queryset = SafetyFeature.objects.all()
    serializer_class = SafetyFeatureSerializer
    lookup_field = "slug"


class FinishOptionViewSet(PublishedViewSet):
    queryset = FinishOption.objects.all()
    serializer_class = FinishOptionSerializer
    filterset_fields = ["category"]


class ComponentViewSet(PublishedViewSet):
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    lookup_field = "slug"
