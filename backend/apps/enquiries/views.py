import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Enquiry, ServiceRequest
from .serializers import EnquirySerializer, ServiceRequestSerializer

log = logging.getLogger(__name__)


def _notify(subject, body):
    """Best-effort notification — a mail failure must never lose the lead."""
    if not settings.ENQUIRY_NOTIFY_TO:
        return
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            settings.ENQUIRY_NOTIFY_TO,
            fail_silently=False,
        )
    except Exception:
        log.exception("Could not send notification for: %s", subject)


class EnquiryViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Enquiry.objects.all()
    serializer_class = EnquirySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = "enquiry"

    def create(self, request, *args, **kwargs):
        data = request.data
        if hasattr(data, "getlist") and data.getlist("uploads"):
            data = data.copy()
            data.setlist("uploads", request.FILES.getlist("uploads"))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        enquiry = serializer.save()
        _notify(
            f"New project enquiry - {enquiry.name}",
            "\n".join(
                [
                    f"Name:      {enquiry.name}",
                    f"Phone:     {enquiry.phone}",
                    f"Email:     {enquiry.email}",
                    f"Org:       {enquiry.organisation or '-'}",
                    f"Property:  {enquiry.get_property_type_display() or '-'}",
                    f"Stage:     {enquiry.get_project_stage_display() or '-'}",
                    f"Location:  {enquiry.location or '-'}",
                    f"Floors:    {enquiry.floors or '-'}",
                    f"Lift:      {enquiry.lift_type or enquiry.lift_type_note or '-'}",
                    f"Capacity:  {enquiry.capacity or '-'}",
                    f"Stops:     {enquiry.stops or '-'}",
                    f"Config:    {enquiry.configuration or '-'}",
                    f"Files:     {enquiry.attachments.count()}",
                    "",
                    enquiry.message or "(no message)",
                ]
            ),
        )
        return Response(
            {
                "id": enquiry.id,
                "reference": f"ZL-{enquiry.created_at:%y%m}-{enquiry.id:04d}",
                "message": "Thank you. Our engineering team will be in touch within one working day.",
            },
            status=status.HTTP_201_CREATED,
        )


class ServiceRequestViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    throttle_scope = "enquiry"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sr = serializer.save()
        _notify(
            f"[{sr.get_urgency_display()}] Service request - {sr.get_kind_display()}",
            "\n".join(
                [
                    f"Name:     {sr.name}",
                    f"Phone:    {sr.phone}",
                    f"Email:    {sr.email or '-'}",
                    f"Site:     {sr.site_name or '-'}",
                    f"Location: {sr.location or '-'}",
                    f"Ref:      {sr.lift_reference or '-'}",
                    "",
                    sr.message or "(no message)",
                ]
            ),
        )
        return Response(
            {
                "id": sr.id,
                "reference": f"SR-{sr.created_at:%y%m}-{sr.id:04d}",
                "message": "Received. Our service desk will call you shortly.",
            },
            status=status.HTTP_201_CREATED,
        )
