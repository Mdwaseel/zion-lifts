"""The anonymous API the website reads, and the two forms it writes.

Reads are unauthenticated, unpaginated and hide unpublished rows — the site
renders whole collections at once, so paging them would only make the front end
reassemble what it asked for.

The two ``*-categories/`` endpoints have no table behind them any more. They
count the rows in each choice and return the ones that exist, which is what the
site actually wanted from those tables: a filter chip with a number on it.

There is no ``faq-categories/`` here any more either, and no stats, milestones,
certifications, service pillars or legal pages. That content never changed
between deploys, so it moved to ``frontend/src/data/`` where the site can render
it without asking.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    Application,
    Award,
    BlogPost,
    Component,
    Enquiry,
    Finish,
    GalleryItem,
    Lift,
    Office,
    Partner,
    Project,
    SafetyFeature,
    ServiceRequest,
    SiteSettings,
    TeamMember,
    Testimonial,
)
from .forms import EnquirySerializer, ServiceRequestSerializer
from .serializers import (
    ApplicationSerializer,
    AwardSerializer,
    BlogPostDetailSerializer,
    BlogPostSerializer,
    ComponentSerializer,
    FinishSerializer,
    GalleryItemSerializer,
    LiftDetailSerializer,
    LiftListSerializer,
    OfficeSerializer,
    PartnerSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    SafetyFeatureSerializer,
    SiteSettingsSerializer,
    TeamMemberSerializer,
    TestimonialSerializer,
)

log = logging.getLogger(__name__)


class PublishedViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only base that hides unpublished rows and skips pagination."""

    pagination_class = None

    def get_queryset(self):
        qs = self.queryset
        if hasattr(qs.model, "is_published"):
            qs = qs.filter(is_published=True)
        return qs


# --------------------------------------------------------------------- catalogue
class LiftViewSet(PublishedViewSet):
    queryset = Lift.objects.prefetch_related("applications", "safety_features")
    lookup_field = "slug"
    search_fields = ["name", "tagline", "summary"]

    def get_serializer_class(self):
        return LiftDetailSerializer if self.action == "retrieve" else LiftListSerializer


class ApplicationViewSet(PublishedViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    lookup_field = "slug"
    filterset_fields = ["group"]


class SafetyFeatureViewSet(PublishedViewSet):
    queryset = SafetyFeature.objects.all()
    serializer_class = SafetyFeatureSerializer
    lookup_field = "slug"


class FinishViewSet(PublishedViewSet):
    queryset = Finish.objects.all()
    serializer_class = FinishSerializer
    filterset_fields = ["category"]


class ComponentViewSet(PublishedViewSet):
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    lookup_field = "slug"


# ---------------------------------------------------------------------- projects
class ProjectViewSet(PublishedViewSet):
    queryset = Project.objects.select_related("lift")
    lookup_field = "slug"
    filterset_fields = ["category", "lift__slug", "is_featured"]
    search_fields = ["name", "client", "location", "summary"]

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.action == "retrieve" else ProjectListSerializer


# ------------------------------------------------------------------------- blogs
class BlogPostViewSet(PublishedViewSet):
    queryset = BlogPost.objects.all()
    lookup_field = "slug"
    filterset_fields = ["category", "is_featured"]
    search_fields = ["title", "excerpt", "body"]

    def get_serializer_class(self):
        return BlogPostDetailSerializer if self.action == "retrieve" else BlogPostSerializer


# --------------------------------------------------------------------- editorial
class TestimonialViewSet(PublishedViewSet):
    queryset = Testimonial.objects.select_related("project")
    serializer_class = TestimonialSerializer
    filterset_fields = ["is_featured"]


class TeamMemberViewSet(PublishedViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    filterset_fields = ["department", "is_leadership"]


class AwardViewSet(PublishedViewSet):
    queryset = Award.objects.all()
    serializer_class = AwardSerializer


class GalleryItemViewSet(PublishedViewSet):
    queryset = GalleryItem.objects.select_related("project")
    serializer_class = GalleryItemSerializer
    filterset_fields = ["category", "is_featured"]


# ------------------------------------------------------ categories, derived
def _counted(model, field: str, choices, descriptions=None, **filters) -> list[dict]:
    """The choices that actually have rows behind them, with their counts.

    ``id`` is the slug rather than an integer. Nothing addresses a category by
    id any more — there is no row to address — and the front end only uses it as
    a React key, so a stable string is better than an invented number.
    """
    counts = dict(
        model.objects.filter(is_published=True, **filters)
        .values_list(field)
        .annotate(n=Count("pk"))
    )
    return [
        {
            "id": slug,
            "slug": slug,
            "name": name,
            "description": (descriptions or {}).get(slug, ""),
            "count": counts.get(slug, 0),
        }
        for slug, name in choices
    ]


class ProjectCategoryView(APIView):
    """The building types, counted. Was a table; is now Project's choices."""

    def get(self, request):
        return Response(
            _counted(
                Project, "category", Project.CATEGORIES, Project.CATEGORY_DESCRIPTIONS
            )
        )


class BlogCategoryView(APIView):
    def get(self, request):
        return Response(_counted(BlogPost, "category", BlogPost.CATEGORIES))


# ------------------------------------------------------------------ organisation
class OfficeViewSet(PublishedViewSet):
    queryset = Office.objects.all()
    serializer_class = OfficeSerializer
    filterset_fields = ["kind"]


class PartnerViewSet(PublishedViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    filterset_fields = ["role"]


class SiteSettingsView(APIView):
    """Everything every page needs, in one request."""

    def get(self, request):
        data = SiteSettingsSerializer(SiteSettings.load(), context={"request": request}).data
        data["offices"] = OfficeSerializer(
            Office.objects.filter(is_published=True), many=True, context={"request": request}
        ).data
        return Response(data)


# ------------------------------------------------------------------------- inbox
def _notify(subject: str, body: str) -> None:
    """Best-effort notification — a mail failure must never lose the lead."""
    if not settings.ENQUIRY_NOTIFY_TO:
        return
    try:
        send_mail(
            subject, body, settings.DEFAULT_FROM_EMAIL, settings.ENQUIRY_NOTIFY_TO,
            fail_silently=False,
        )
    except Exception:
        log.exception("Could not send notification for: %s", subject)


class EnquiryViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Create only. Reading enquiries is the control room's job, not the site's."""

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
                    f"Lift:      {enquiry.lift or enquiry.lift_type_note or '-'}",
                    f"Capacity:  {enquiry.capacity or '-'}",
                    f"Stops:     {enquiry.stops or '-'}",
                    f"Config:    {enquiry.configuration or '-'}",
                    f"Files:     {enquiry.attachment_count}",
                    "",
                    enquiry.message or "(no message)",
                ]
            ),
        )
        return Response(
            {
                "id": enquiry.id,
                "reference": enquiry.reference,
                "message": "Thank you. Our engineering team will be in touch "
                "within one working day.",
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
        service_request = serializer.save()

        _notify(
            f"[{service_request.get_urgency_display()}] Service request - "
            f"{service_request.get_kind_display()}",
            "\n".join(
                [
                    f"Name:     {service_request.name}",
                    f"Phone:    {service_request.phone}",
                    f"Email:    {service_request.email or '-'}",
                    f"Site:     {service_request.site_name or '-'}",
                    f"Location: {service_request.location or '-'}",
                    f"Ref:      {service_request.lift_reference or '-'}",
                    "",
                    service_request.message or "(no message)",
                ]
            ),
        )
        return Response(
            {
                "id": service_request.id,
                "reference": service_request.reference,
                "message": "Received. Our service desk will call you shortly.",
            },
            status=status.HTTP_201_CREATED,
        )
