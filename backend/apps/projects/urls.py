from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProjectCategoryViewSet, ProjectViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet)
router.register("project-categories", ProjectCategoryViewSet)

urlpatterns = [path("", include(router.urls))]
