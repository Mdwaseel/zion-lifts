"""Knowledge routes, mounted under /api/admin/knowledge/.

Beside the registry-driven collections rather than inside them: these endpoints
are operations (upload, reindex, retry, delete) that the generic resource
viewset has no vocabulary for. Browsing and filtering the same records still
happens through the registry, at /api/admin/knowledge-documents/.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet, IngestionJobViewSet, KnowledgeBaseViewSet

app_name = "knowledge"

router = DefaultRouter()
router.register("bases", KnowledgeBaseViewSet, basename="knowledge-base")
router.register("documents", DocumentViewSet, basename="knowledge-document")
router.register("jobs", IngestionJobViewSet, basename="knowledge-job")

urlpatterns = [path("", include(router.urls))]
