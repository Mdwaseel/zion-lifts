from apps.core.views import PublishedViewSet

from .models import Project, ProjectCategory
from .serializers import (
    ProjectCategorySerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
)


class ProjectViewSet(PublishedViewSet):
    queryset = Project.objects.select_related("category", "lift_type").prefetch_related("images")
    lookup_field = "slug"
    filterset_fields = ["category__slug", "lift_type__slug", "is_featured"]
    search_fields = ["name", "client", "location", "summary"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectListSerializer


class ProjectCategoryViewSet(PublishedViewSet):
    queryset = ProjectCategory.objects.all()
    serializer_class = ProjectCategorySerializer
    lookup_field = "slug"
