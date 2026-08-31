from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Certification, Office, Partner, SiteSettings, Stat
from .serializers import (
    CertificationSerializer,
    OfficeSerializer,
    PartnerSerializer,
    SiteSettingsSerializer,
    StatSerializer,
)


class PublishedViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only base that hides unpublished rows and skips pagination."""

    pagination_class = None

    def get_queryset(self):
        qs = self.queryset
        if hasattr(qs.model, "is_published"):
            qs = qs.filter(is_published=True)
        return qs


class OfficeViewSet(PublishedViewSet):
    queryset = Office.objects.all()
    serializer_class = OfficeSerializer
    filterset_fields = ["kind"]


class StatViewSet(PublishedViewSet):
    queryset = Stat.objects.all()
    serializer_class = StatSerializer
    filterset_fields = ["group"]


class PartnerViewSet(PublishedViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    filterset_fields = ["role"]


class CertificationViewSet(PublishedViewSet):
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer


class SiteSettingsView(APIView):
    def get(self, request):
        data = SiteSettingsSerializer(SiteSettings.load(), context={"request": request}).data
        data["offices"] = OfficeSerializer(
            Office.objects.filter(is_published=True), many=True, context={"request": request}
        ).data
        return Response(data)
