from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AwardViewSet,
    FAQCategoryViewSet,
    GalleryItemViewSet,
    JournalCategoryViewSet,
    JournalPostViewSet,
    LegalDocumentViewSet,
    MilestoneViewSet,
    ServicePillarViewSet,
    TeamMemberViewSet,
    TestimonialViewSet,
)

router = DefaultRouter()
router.register("faq-categories", FAQCategoryViewSet)
router.register("journal-categories", JournalCategoryViewSet)
router.register("journal", JournalPostViewSet)
router.register("testimonials", TestimonialViewSet)
router.register("milestones", MilestoneViewSet)
router.register("team", TeamMemberViewSet)
router.register("awards", AwardViewSet)
router.register("service-pillars", ServicePillarViewSet)
router.register("gallery", GalleryItemViewSet)
router.register("legal", LegalDocumentViewSet)

urlpatterns = [path("", include(router.urls))]
