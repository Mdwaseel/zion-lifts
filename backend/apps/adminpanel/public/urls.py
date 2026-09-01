"""The website's routes, under ``/api/``.

Every path here is one the React app already calls, unchanged. ``journal/``
still says journal even though the model is now ``BlogPost``, and
``service-requests/`` still says service-requests — a rename on this side is not
a reason to break a URL the site, and anything else pointed at it, already uses.

The two ``*-categories/`` paths are plain views rather than router entries:
there is no category table left to give them a detail route to.

Six collections that used to be here are gone entirely — FAQs, milestones,
certifications, service pillars, stats and the legal pages. They were static
text served over HTTP, so they are static modules in ``frontend/src/data/``
now and the site renders them on the first paint instead of after a round trip.
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
router.register("team", views.TeamMemberViewSet, basename="team")
router.register("awards", views.AwardViewSet, basename="awards")
router.register("gallery", views.GalleryItemViewSet, basename="gallery")

# organisation
router.register("offices", views.OfficeViewSet, basename="offices")
router.register("partners", views.PartnerViewSet, basename="partners")

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
    path("", include(router.urls)),
]
