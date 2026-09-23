"""The two things the public may write: an enquiry and a service request.

Separate from ``serializers.py`` because the rules are different in kind. Those
serialisers describe published content going out; these validate a stranger's
input coming in — file types, sizes, consent, and a honeypot — and they are the
only writable surface the anonymous API has.

Attachments no longer create rows. Each accepted file is written to storage
here and recorded as an entry in the enquiry's ``attachments`` list, which is
the whole of what the old ``EnquiryAttachment`` table held.
"""

from __future__ import annotations

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import serializers

from ..models import Enquiry, Lift, ServiceRequest

MAX_ATTACHMENTS = 6
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".dwg", ".dxf"}


def store_attachment(upload) -> dict:
    """Write one upload and describe it the way the JSON column expects.

    Partitioned by month, as the old ``upload_to`` was. ``default_storage``
    appends a suffix if the name is taken, so two people sending "plan.pdf" in
    the same month keep two files.
    """
    today = timezone.localdate()
    path = default_storage.save(
        f"enquiries/{today:%Y}/{today:%m}/{upload.name}", upload
    )
    return {
        "name": upload.name[:200],
        "path": path,
        "url": default_storage.url(path),
        "size": upload.size,
        "uploaded_at": timezone.now().isoformat(),
    }


class HoneypotMixin(serializers.Serializer):
    """A field the form renders off-screen. Real people never fill it in."""

    website = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.pop("website", ""):
            raise serializers.ValidationError("Submission rejected.")
        return attrs


class EnquirySerializer(HoneypotMixin, serializers.ModelSerializer):
    uploads = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )
    # The form posts the chosen lift as ``lift_type``, the name it has had since
    # the first version of the site. Accepted under that name so the front end
    # does not have to change for a rename on this side.
    lift_type = serializers.PrimaryKeyRelatedField(
        source="lift",
        queryset=Lift.objects.all(),
        required=False,
        allow_null=True,
    )
    attachments = serializers.JSONField(read_only=True)

    class Meta:
        model = Enquiry
        fields = [
            "id", "property_type", "project_stage", "location", "floors",
            "lift_type", "lift_type_note", "capacity", "stops", "installation_kind",
            "configuration", "name", "phone", "email", "organisation", "message",
            "consent", "source_path", "attachments", "uploads", "website", "created_at",
        ]
        read_only_fields = ["id", "created_at", "attachments"]

    def validate_uploads(self, files):
        if len(files) > MAX_ATTACHMENTS:
            raise serializers.ValidationError(
                f"Please attach at most {MAX_ATTACHMENTS} files."
            )
        for upload in files:
            suffix = (
                "." + upload.name.rsplit(".", 1)[-1]
            ).lower() if "." in upload.name else ""
            if suffix not in ALLOWED_SUFFIXES:
                raise serializers.ValidationError(
                    f"{upload.name}: only PDF, JPG, PNG, WEBP, DWG and DXF "
                    "drawings are accepted."
                )
            if upload.size > MAX_ATTACHMENT_BYTES:
                raise serializers.ValidationError(f"{upload.name} is larger than 10 MB.")
        return files

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "Please confirm you are happy for us to contact you about this enquiry."
            )
        return value

    def create(self, validated_data):
        uploads = validated_data.pop("uploads", [])
        validated_data["attachments"] = [store_attachment(f) for f in uploads]
        return Enquiry.objects.create(**validated_data)


class ServiceRequestSerializer(HoneypotMixin, serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = [
            "id", "kind", "urgency", "name", "phone", "email", "site_name",
            "location", "lift_reference", "message", "consent", "website", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Please confirm we may contact you.")
        return value
