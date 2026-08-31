"""Shapes for the knowledge API.

Read serializers are flat and denormalised on purpose: the control room's
document table shows the knowledge base, the live version and the last job's
progress in one row, and three round trips to fill one row is not a table.
"""

from __future__ import annotations

from rest_framework import serializers

from ..models import Document, DocumentVersion, IngestionJob, KnowledgeBase
from ..states import IN_FLIGHT, DocumentState
from ..validators import MAX_UPLOAD_BYTES


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(read_only=True)
    ready_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = (
            "id", "name", "slug", "description", "is_active",
            "document_count", "ready_count", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class DocumentVersionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentVersion
        fields = (
            "id", "version_number", "status", "is_active",
            "content_hash", "file_size", "page_count", "chunk_count",
            "embedding_model", "embedding_model_version", "embedding_dimension",
            "collection", "error_code", "error_message", "created_at",
        )
        read_only_fields = fields


class IngestionJobSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = IngestionJob
        fields = (
            "id", "job_type", "status", "progress", "current_stage",
            "attempt_count", "celery_task_id", "error_code", "error_message",
            "started_at", "finished_at", "duration_seconds", "created_at",
        )
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    knowledge_base_name = serializers.CharField(source="knowledge_base.name", read_only=True)
    active_version_number = serializers.IntegerField(
        source="active_version.version_number", read_only=True, default=None
    )
    version_count = serializers.IntegerField(read_only=True, default=None)
    # Denormalised from the live edition. The control room's document table
    # shows them on every row, and reaching through to each version to fill a
    # column is how a fifty-row table becomes fifty-one queries.
    page_count = serializers.IntegerField(
        source="active_version.page_count", read_only=True, default=None
    )
    chunk_count = serializers.IntegerField(
        source="active_version.chunk_count", read_only=True, default=None
    )
    is_processing = serializers.SerializerMethodField()
    latest_job = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id", "name", "knowledge_base", "knowledge_base_name",
            "original_filename", "mime_type", "file_size", "status",
            "active_version", "active_version_number", "version_count",
            "page_count", "chunk_count",
            "is_processing", "latest_job", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "original_filename", "mime_type", "file_size", "status",
            "active_version", "created_at", "updated_at",
        )

    def get_is_processing(self, obj: Document) -> bool:
        return obj.status in IN_FLIGHT

    def get_latest_job(self, obj: Document) -> dict | None:
        """The most recent attempt, so a row can show progress without a
        second request. Uses the prefetch the view sets up rather than
        querying — see ``DocumentViewSet.get_queryset``."""
        jobs = getattr(obj, "recent_jobs", None)
        job = jobs[0] if jobs else None
        if job is None:
            return None
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "current_stage": job.current_stage,
            "error_code": job.error_code,
        }


class DocumentUploadSerializer(serializers.Serializer):
    """A new document. The file itself is validated in the service layer, by
    ``validators.validate_upload`` — the checks there look at the bytes, not
    just at what the request claims about them."""

    knowledge_base = serializers.PrimaryKeyRelatedField(
        queryset=KnowledgeBase.objects.filter(is_active=True)
    )
    file = serializers.FileField(max_length=255, allow_empty_file=False)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_file(self, value):
        # A cheap early rejection so an oversized upload is refused before the
        # service hashes it. The authoritative limit is in the validator.
        if value.size and value.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError(
                f"That file is {value.size / 1024 / 1024:.1f} MB; the limit is "
                f"{MAX_UPLOAD_BYTES / 1024 / 1024:.0f} MB."
            )
        return value


class VersionUploadSerializer(serializers.Serializer):
    """A replacement edition of an existing document."""

    file = serializers.FileField(max_length=255, allow_empty_file=False)
    allow_duplicate = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Re-process bytes already stored as a version of this document.",
    )


class IngestionReportSerializer(serializers.Serializer):
    """One status update from the ingestion worker.

    Mirrors ``IngestionReport`` in ai_service/app/api/schemas/document.py. The
    two are a shared contract that no import enforces, so they change together.

    Counts are accepted only as reported values to *store*; nothing here is
    trusted to decide a transition. That is ``job_service.apply_report``'s job,
    which checks the move against the lifecycle before writing anything.
    """

    job_id = serializers.UUIDField()
    document_id = serializers.UUIDField()
    document_version_id = serializers.UUIDField()

    stage = serializers.ChoiceField(choices=DocumentState.choices)
    progress = serializers.IntegerField(min_value=0, max_value=100, required=False, default=0)

    page_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    chunk_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)

    embedding_model = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )
    embedding_model_version = serializers.CharField(
        max_length=40, required=False, allow_blank=True, allow_null=True
    )
    embedding_dimension = serializers.IntegerField(
        min_value=1, required=False, allow_null=True
    )
    collection = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )

    error_code = serializers.CharField(
        max_length=80, required=False, allow_blank=True, allow_null=True
    )
    error_message = serializers.CharField(
        max_length=8000, required=False, allow_blank=True, allow_null=True
    )

    def validate(self, attrs):
        if attrs["stage"] == DocumentState.FAILED and not attrs.get("error_code"):
            raise serializers.ValidationError(
                {"error_code": "A failure report must name an error code."}
            )
        return attrs
