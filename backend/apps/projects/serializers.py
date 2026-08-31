from rest_framework import serializers

from apps.core.serializers import AssetField

from .models import Project, ProjectCategory, ProjectImage


class ProjectCategorySerializer(serializers.ModelSerializer):
    count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectCategory
        fields = ["id", "slug", "name", "description", "count"]

    def get_count(self, obj):
        return obj.projects.filter(is_published=True).count()


class ProjectImageSerializer(serializers.ModelSerializer):
    src = AssetField("image", "image_url")

    class Meta:
        model = ProjectImage
        fields = ["id", "stage", "src", "caption", "alt"]


class ProjectListSerializer(serializers.ModelSerializer):
    category = ProjectCategorySerializer(read_only=True)
    lift_type_slug = serializers.CharField(source="lift_type.slug", default="", read_only=True)
    lift_type_name = serializers.CharField(source="lift_type.name", default="", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "slug", "name", "client", "location", "year", "category",
            "lift_type_slug", "lift_type_name", "statement", "summary",
            "system", "capacity", "stops", "scope",
            "hero_image_url", "poster_url", "loop_video_url",
            "is_portrait", "is_featured",
        ]


class ProjectDetailSerializer(ProjectListSerializer):
    images = ProjectImageSerializer(many=True, read_only=True)
    related = serializers.SerializerMethodField()

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + [
            "challenge", "solution", "result", "door", "drive",
            "hero_video_url", "images", "related",
        ]

    def get_related(self, obj):
        qs = Project.objects.filter(is_published=True).exclude(pk=obj.pk)
        if obj.category_id:
            picks = list(qs.filter(category_id=obj.category_id)[:3])
            if len(picks) < 3:
                picks += list(qs.exclude(category_id=obj.category_id)[: 3 - len(picks)])
        else:
            picks = list(qs[:3])
        return ProjectListSerializer(picks, many=True, context=self.context).data
