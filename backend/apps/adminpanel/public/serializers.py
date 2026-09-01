"""What the website receives.

The JSON here is unchanged from what the site read before the models were
consolidated — the same keys, the same nesting, the same types. That is the
point: collapsing five tables into one row is a decision about how content is
*stored and edited*, and the front end should not have to know it happened.

Two shapes are worth naming, because they are where the old tables went:

* ``category`` still serialises as ``{"slug", "name"}``. It is built from the
  model's choices now instead of a joined row, so nothing on the site changes
  and there is no second table to keep in step.
* ``images``/``variants``/``specs`` still serialise as lists of objects. They
  are read straight off the JSON column, so the detail endpoints no longer fan
  out into one query per child table.

Absent here on purpose: FAQs, milestones, certifications, service pillars, stats
and legal pages. They were serialised text that never changed, and they are now
static modules under ``frontend/src/data/``.
"""

from __future__ import annotations

from rest_framework import serializers

from ..models import (
    Application,
    Award,
    BlogPost,
    Component,
    Finish,
    GalleryItem,
    Lift,
    Office,
    Partner,
    Project,
    SafetyFeature,
    SiteSettings,
    TeamMember,
    Testimonial,
)


class AssetField(serializers.Field):
    """Emit a usable URL whether the asset is uploaded or a static public path."""

    def __init__(self, file_attr, url_attr=None, **kwargs):
        self.file_attr = file_attr
        self.url_attr = url_attr
        kwargs.setdefault("source", "*")
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, obj):
        stored = getattr(obj, self.file_attr, None)
        if stored:
            request = self.context.get("request")
            return request.build_absolute_uri(stored.url) if request else stored.url
        if self.url_attr:
            return getattr(obj, self.url_attr, "") or None
        return None


class CategoryField(serializers.Field):
    """A choice, rendered the way the site's filter chips expect a category.

    The front end reads ``post.category.slug`` and ``post.category.name``. It
    kept doing so after ``JournalCategory`` stopped being a table, because this
    field turns the stored slug back into the pair using the model's own
    ``choices`` — one source of truth, no join.
    """

    def __init__(self, choices, **kwargs):
        self.labels = dict(choices)
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        return {"slug": value, "name": self.labels.get(value, value)}


# --------------------------------------------------------------------- catalogue
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["id", "slug", "name", "group", "description", "image_url"]


class SafetyFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyFeature
        fields = [
            "id", "slug", "name", "headline", "description",
            "test_procedure", "standard", "media_url",
        ]


class FinishSerializer(serializers.ModelSerializer):
    texture = AssetField("texture", "texture_url")

    class Meta:
        model = Finish
        fields = [
            "id", "category", "slug", "name", "description",
            "swatch_hex", "swatch_hex_2", "texture", "tier",
        ]


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ["id", "slug", "index", "name", "description", "detail", "supplier"]


class LiftListSerializer(serializers.ModelSerializer):
    applications = ApplicationSerializer(many=True, read_only=True)

    class Meta:
        model = Lift
        fields = [
            "id", "slug", "name", "short_name", "eyebrow", "tagline", "summary",
            "speed", "capacity", "stops", "drive",
            "min_floors", "max_floors", "min_persons", "max_persons",
            "machine_room", "hero_image_url", "hero_video_url", "accent",
            "applications", "is_featured", "order",
        ]


class LiftDetailSerializer(LiftListSerializer):
    safety_features = SafetyFeatureSerializer(many=True, read_only=True)
    related = serializers.SerializerMethodField()

    class Meta(LiftListSerializer.Meta):
        fields = LiftListSerializer.Meta.fields + [
            "overview", "pit_depth", "headroom", "shaft_footprint",
            "images", "variants", "specs", "safety_features", "related",
        ]

    def get_related(self, obj):
        others = (
            Lift.objects.filter(is_published=True)
            .exclude(pk=obj.pk)
            .prefetch_related("applications")[:6]
        )
        return LiftListSerializer(others, many=True, context=self.context).data


# ---------------------------------------------------------------------- projects
class ProjectListSerializer(serializers.ModelSerializer):
    category = CategoryField(Project.CATEGORIES)
    lift_type_slug = serializers.CharField(source="lift.slug", default="", read_only=True)
    lift_type_name = serializers.CharField(source="lift.name", default="", read_only=True)

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
    related = serializers.SerializerMethodField()

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + [
            "challenge", "solution", "result", "door", "drive",
            "hero_video_url", "images", "related",
        ]

    def get_related(self, obj):
        others = (
            Project.objects.filter(is_published=True)
            .exclude(pk=obj.pk)
            .select_related("lift")
        )
        # Same building type first, topped up with anything else rather than
        # showing two cards where the layout wants three.
        picks = list(others.filter(category=obj.category)[:3])
        if len(picks) < 3:
            picks += list(others.exclude(category=obj.category)[: 3 - len(picks)])
        return ProjectListSerializer(picks, many=True, context=self.context).data


# ------------------------------------------------------------------------- blogs
class BlogPostSerializer(serializers.ModelSerializer):
    category = CategoryField(BlogPost.CATEGORIES)

    class Meta:
        model = BlogPost
        fields = [
            "id", "slug", "title", "category", "excerpt", "hero_image_url",
            "read_minutes", "published_at", "is_featured",
        ]


class BlogPostDetailSerializer(BlogPostSerializer):
    related = serializers.SerializerMethodField()

    class Meta(BlogPostSerializer.Meta):
        fields = BlogPostSerializer.Meta.fields + ["body", "related"]

    def get_related(self, obj):
        others = BlogPost.objects.filter(is_published=True).exclude(pk=obj.pk)[:3]
        return BlogPostSerializer(others, many=True, context=self.context).data


# --------------------------------------------------------------------- editorial
class TestimonialSerializer(serializers.ModelSerializer):
    project_slug = serializers.CharField(source="project.slug", default="", read_only=True)

    class Meta:
        model = Testimonial
        fields = [
            "id", "name", "role", "organisation", "location", "quote",
            "video_url", "poster_url", "project_slug", "is_featured",
        ]


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = AssetField("photo", "photo_url")
    department_display = serializers.CharField(source="get_department_display", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id", "name", "role", "department", "department_display",
            "bio", "photo",
        ]


class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Award
        fields = ["id", "name", "organisation", "year", "description", "image_url"]


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


# ------------------------------------------------------------------ organisation
class OfficeSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Office
        fields = [
            "id", "kind", "kind_display", "name", "address", "locality", "city",
            "state", "postcode", "phone", "email", "hours", "note",
            "latitude", "longitude", "map_embed_url", "directions_url",
        ]


class PartnerSerializer(serializers.ModelSerializer):
    logo = AssetField("logo", "logo_url")
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Partner
        fields = ["id", "name", "role", "role_display", "component", "logo", "website"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        exclude = ["id", "created_at", "updated_at"]
