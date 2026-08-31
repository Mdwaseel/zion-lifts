from rest_framework import serializers

from apps.core.serializers import AssetField

from .models import (
    FAQ,
    Award,
    FAQCategory,
    GalleryItem,
    JournalCategory,
    JournalPost,
    LegalClause,
    LegalDocument,
    Milestone,
    ServicePillar,
    TeamMember,
    Testimonial,
)


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "link_label", "link_url", "scope"]


class FAQCategorySerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()

    class Meta:
        model = FAQCategory
        fields = ["id", "slug", "name", "description", "count", "questions"]

    def _visible(self, obj):
        qs = obj.questions.filter(is_published=True)
        scope = self.context.get("request").query_params.get("scope") if self.context.get("request") else None
        if scope:
            qs = qs.filter(scope=scope)
        return qs

    def get_questions(self, obj):
        return FAQSerializer(self._visible(obj), many=True).data

    def get_count(self, obj):
        return self._visible(obj).count()


class JournalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalCategory
        fields = ["id", "slug", "name"]


class JournalPostSerializer(serializers.ModelSerializer):
    category = JournalCategorySerializer(read_only=True)

    class Meta:
        model = JournalPost
        fields = [
            "id", "slug", "title", "category", "excerpt", "hero_image_url",
            "read_minutes", "published_at", "is_featured",
        ]


class JournalPostDetailSerializer(JournalPostSerializer):
    related = serializers.SerializerMethodField()

    class Meta(JournalPostSerializer.Meta):
        fields = JournalPostSerializer.Meta.fields + ["body", "related"]

    def get_related(self, obj):
        qs = JournalPost.objects.filter(is_published=True).exclude(pk=obj.pk)[:3]
        return JournalPostSerializer(qs, many=True, context=self.context).data


class TestimonialSerializer(serializers.ModelSerializer):
    project_slug = serializers.CharField(source="project.slug", default="", read_only=True)

    class Meta:
        model = Testimonial
        fields = [
            "id", "name", "role", "organisation", "location", "quote",
            "video_url", "poster_url", "project_slug", "is_featured",
        ]


class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = ["id", "year", "title", "description", "image_url"]


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = AssetField("photo", "photo_url")
    department_display = serializers.CharField(source="get_department_display", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id", "name", "role", "department", "department_display",
            "bio", "photo", "is_leadership",
        ]


class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Award
        fields = ["id", "name", "organisation", "year", "description", "image_url"]


class ServicePillarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePillar
        fields = ["id", "slug", "name", "description", "detail", "icon"]


class GalleryItemSerializer(serializers.ModelSerializer):
    src = AssetField("image", "image_url")
    aspect = serializers.FloatField(read_only=True)
    project_slug = serializers.CharField(source="project.slug", default="", read_only=True)

    class Meta:
        model = GalleryItem
        fields = [
            "id", "category", "title", "meta", "src", "width", "height",
            "aspect", "project_slug", "is_featured",
        ]


class LegalClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalClause
        fields = ["id", "heading", "body"]


class LegalDocumentSerializer(serializers.ModelSerializer):
    clauses = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = ["id", "slug", "title", "intro", "effective_date", "clauses"]

    def get_clauses(self, obj):
        return LegalClauseSerializer(obj.clauses.filter(is_published=True), many=True).data
