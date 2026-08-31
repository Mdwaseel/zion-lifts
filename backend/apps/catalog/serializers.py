from rest_framework import serializers

from apps.core.serializers import AssetField

from .models import (
    Application,
    Component,
    FinishOption,
    LiftImage,
    LiftSpec,
    LiftType,
    LiftVariant,
    SafetyFeature,
)


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


class FinishOptionSerializer(serializers.ModelSerializer):
    texture = AssetField("texture", "texture_url")

    class Meta:
        model = FinishOption
        fields = [
            "id", "category", "slug", "name", "description",
            "swatch_hex", "swatch_hex_2", "texture", "tier",
        ]


class LiftImageSerializer(serializers.ModelSerializer):
    src = AssetField("image", "image_url")

    class Meta:
        model = LiftImage
        fields = ["id", "kind", "src", "alt", "caption"]


class LiftVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiftVariant
        fields = ["id", "code", "name", "description", "capacity", "persons", "speed", "shaft"]


class LiftSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiftSpec
        fields = ["id", "group", "label", "value", "note"]


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ["id", "slug", "index", "name", "description", "detail", "supplier"]


class LiftTypeListSerializer(serializers.ModelSerializer):
    applications = ApplicationSerializer(many=True, read_only=True)

    class Meta:
        model = LiftType
        fields = [
            "id", "slug", "name", "short_name", "eyebrow", "tagline", "summary",
            "speed", "capacity", "stops", "drive",
            "min_floors", "max_floors", "min_persons", "max_persons",
            "machine_room", "hero_image_url", "hero_video_url", "accent",
            "applications", "is_featured", "order",
        ]


class LiftTypeDetailSerializer(LiftTypeListSerializer):
    images = LiftImageSerializer(many=True, read_only=True)
    variants = LiftVariantSerializer(many=True, read_only=True)
    specs = LiftSpecSerializer(many=True, read_only=True)
    safety_features = SafetyFeatureSerializer(many=True, read_only=True)
    related = serializers.SerializerMethodField()

    class Meta(LiftTypeListSerializer.Meta):
        fields = LiftTypeListSerializer.Meta.fields + [
            "overview", "pit_depth", "headroom", "shaft_footprint",
            "images", "variants", "specs", "safety_features", "related",
        ]

    def get_related(self, obj):
        qs = LiftType.objects.filter(is_published=True).exclude(pk=obj.pk)[:6]
        return LiftTypeListSerializer(qs, many=True, context=self.context).data
