"""The website's routes, under ``/api/``.

Every path here is one the React app already calls, unchanged. ``journal/``
still says journal even though the model is now ``BlogPost``, and
``service-requests/`` still says service-requests — a rename on this side is not
a reason to break a URL the site, and anything else pointed at it, already uses.

The three ``*-categories/`` paths are plain views rather than router entries:
there is no category table left to give them a detail route to.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "public"

router = DefaultRouter()

# catalogue
router.register("lifts", views.LiftViewSet, basename="lifts")
router.register("applications", views.ApplicationViewSet, basename="applications")
router.register("safety-features", views.SafetyFeatureViewSet, basename="safety-features")
router.register("finishes", views.FinishViewSet, basename="finishes")
router.register("components", views.ComponentViewSet, basename="components")

# projects and blogs
router.register("projects", views.ProjectViewSet, basename="projects")
router.register("journal", views.BlogPostViewSet, basename="journal")

# editorial
router.register("testimonials", views.TestimonialViewSet, basename="testimonials")
router.register("milestones", views.MilestoneViewSet, basename="milestones")
router.register("team", views.TeamMemberViewSet, basename="team")
router.register("awards", views.AwardViewSet, basename="awards")
router.register("service-pillars", views.ServicePillarViewSet, basename="service-pillars")
router.register("gallery", views.GalleryItemViewSet, basename="gallery")
router.register("legal", views.LegalPageViewSet, basename="legal")

# organisation
router.register("offices", views.OfficeViewSet, basename="offices")
router.register("stats", views.StatViewSet, basename="stats")
router.register("partners", views.PartnerViewSet, basename="partners")
router.register("certifications", views.CertificationViewSet, basename="certifications")

# the two forms
router.register("enquiries", views.EnquiryViewSet, basename="enquiries")
router.register("service-requests", views.ServiceRequestViewSet, basename="service-requests")

urlpatterns = [
    path("site/", views.SiteSettingsView.as_view(), name="site-settings"),
    path(
        "project-categories/",
        views.ProjectCategoryView.as_view(),
        name="project-categories",
    ),
    path(
        "journal-categories/",
        views.BlogCategoryView.as_view(),
        name="journal-categories",
    ),
    path("faq-categories/", views.FAQCategoryView.as_view(), name="faq-categories"),
    path("", include(router.urls)),
]
