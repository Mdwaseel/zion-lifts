from rest_framework import serializers

from .models import Certification, Office, Partner, SiteSettings, Stat


class AssetField(serializers.Field):
    """Emit a usable URL whether the asset is uploaded or a static public path."""

    def __init__(self, file_attr, url_attr=None, **kwargs):
        self.file_attr = file_attr
        self.url_attr = url_attr
        kwargs.setdefault("source", "*")
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, obj):
        f = getattr(obj, self.file_attr, None)
        if f:
            request = self.context.get("request")
            return request.build_absolute_uri(f.url) if request else f.url
        if self.url_attr:
            return getattr(obj, self.url_attr, "") or None
        return None


class OfficeSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Office
        fields = [
            "id", "kind", "kind_display", "name", "address", "locality", "city",
            "state", "postcode", "phone", "email", "hours", "note",
            "latitude", "longitude", "map_embed_url", "directions_url",
        ]


class StatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stat
        fields = ["id", "group", "value", "label", "caption", "count_from"]


class PartnerSerializer(serializers.ModelSerializer):
    logo = AssetField("logo", "logo_url")
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Partner
        fields = ["id", "name", "role", "role_display", "component", "logo", "website"]


class CertificationSerializer(serializers.ModelSerializer):
    certificate = AssetField("certificate", "certificate_url")

    class Meta:
        model = Certification
        fields = ["id", "name", "issuer", "reference", "description", "certificate"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        exclude = ["id", "created_at", "updated_at"]
