from rest_framework import serializers

from .models import Enquiry, EnquiryAttachment, ServiceRequest

MAX_ATTACHMENTS = 6
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".dwg", ".dxf"}


class EnquiryAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnquiryAttachment
        fields = ["id", "file", "original_name", "uploaded_at"]
        read_only_fields = ["id", "original_name", "uploaded_at"]


class EnquirySerializer(serializers.ModelSerializer):
    attachments = EnquiryAttachmentSerializer(many=True, read_only=True)
    uploads = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )
    # a honeypot the form renders off-screen; real people never fill it
    website = serializers.CharField(write_only=True, required=False, allow_blank=True)

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
        for f in files:
            suffix = ("." + f.name.rsplit(".", 1)[-1]).lower() if "." in f.name else ""
            if suffix not in ALLOWED_SUFFIXES:
                raise serializers.ValidationError(
                    f"{f.name}: only PDF, JPG, PNG, WEBP, DWG and DXF drawings are accepted."
                )
            if f.size > MAX_ATTACHMENT_BYTES:
                raise serializers.ValidationError(f"{f.name} is larger than 10 MB.")
        return files

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "Please confirm you are happy for us to contact you about this enquiry."
            )
        return value

    def validate(self, attrs):
        if attrs.pop("website", ""):
            raise serializers.ValidationError("Submission rejected.")
        return attrs

    def create(self, validated_data):
        uploads = validated_data.pop("uploads", [])
        enquiry = Enquiry.objects.create(**validated_data)
        for f in uploads:
            EnquiryAttachment.objects.create(
                enquiry=enquiry, file=f, original_name=f.name[:200]
            )
        return enquiry


class ServiceRequestSerializer(serializers.ModelSerializer):
    website = serializers.CharField(write_only=True, required=False, allow_blank=True)

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

    def validate(self, attrs):
        if attrs.pop("website", ""):
            raise serializers.ValidationError("Submission rejected.")
        return attrs
