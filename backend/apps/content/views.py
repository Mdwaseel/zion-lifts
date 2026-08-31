from apps.core.views import PublishedViewSet
from rest_framework import viewsets

from .models import (
    Award,
    FAQCategory,
    GalleryItem,
    JournalCategory,
    JournalPost,
    LegalDocument,
    Milestone,
    ServicePillar,
    TeamMember,
    Testimonial,
)
from .serializers import (
    AwardSerializer,
    FAQCategorySerializer,
    GalleryItemSerializer,
    JournalCategorySerializer,
    JournalPostDetailSerializer,
    JournalPostSerializer,
    LegalDocumentSerializer,
    MilestoneSerializer,
    ServicePillarSerializer,
    TeamMemberSerializer,
    TestimonialSerializer,
)


class FAQCategoryViewSet(PublishedViewSet):
    queryset = FAQCategory.objects.prefetch_related("questions")
    serializer_class = FAQCategorySerializer
    lookup_field = "slug"


class JournalCategoryViewSet(PublishedViewSet):
    queryset = JournalCategory.objects.all()
    serializer_class = JournalCategorySerializer
    lookup_field = "slug"


class JournalPostViewSet(PublishedViewSet):
    queryset = JournalPost.objects.select_related("category")
    lookup_field = "slug"
    filterset_fields = ["category__slug", "is_featured"]
    search_fields = ["title", "excerpt", "body"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return JournalPostDetailSerializer
        return JournalPostSerializer


class TestimonialViewSet(PublishedViewSet):
    queryset = Testimonial.objects.select_related("project")
    serializer_class = TestimonialSerializer
    filterset_fields = ["is_featured"]


class MilestoneViewSet(PublishedViewSet):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer


class TeamMemberViewSet(PublishedViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    filterset_fields = ["department", "is_leadership"]


class AwardViewSet(PublishedViewSet):
    queryset = Award.objects.all()
    serializer_class = AwardSerializer


class ServicePillarViewSet(PublishedViewSet):
    queryset = ServicePillar.objects.all()
    serializer_class = ServicePillarSerializer
    lookup_field = "slug"


class GalleryItemViewSet(PublishedViewSet):
    queryset = GalleryItem.objects.select_related("project")
    serializer_class = GalleryItemSerializer
    filterset_fields = ["category", "is_featured"]


class LegalDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LegalDocument.objects.prefetch_related("clauses")
    serializer_class = LegalDocumentSerializer
    lookup_field = "slug"
    pagination_class = None
