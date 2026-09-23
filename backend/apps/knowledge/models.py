"""The records the site owns about its own knowledge base.

Ownership is the point of this app. The vector index is a *derived*
representation — rebuildable, disposable, and wrong to ask questions like "who
uploaded this?" or "which edition is live?". Those answers live here, in
Postgres, next to the users and permissions that already live here.

The chain is deliberate:

    KnowledgeBase -> Document -> DocumentVersion -> IngestionJob -> vectors

A Document is the thing an operator thinks about ("the 2026 warranty policy").
A DocumentVersion is one immutable edition of its bytes, and it is what gets
indexed — so replacing a document does not disturb the edition currently
answering questions, and a failed re-index leaves the previous one serving.

Identifiers are UUIDs here, unlike the rest of the site's models. These four
cross a service boundary: they travel through Redis to a worker this process
cannot see, and they are written into vector payloads that outlive any single
database. A sequential integer in that position is both guessable and unsafe to
compare across environments.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.adminpanel.models import TimeStamped

from .states import DocumentState, InvalidTransition, check, progress_for


def document_upload_path(instance: DocumentVersion, filename: str) -> str:
    """Where an uploaded edition is stored.

    Partitioned by document id so every edition of one document sits together,
    and named by version so two uploads of the same filename cannot collide.
    The extension is taken from the stored original name, which the serializer
    has already sanitised — nothing user-supplied reaches this path whole.
    """
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"knowledge/{instance.document_id}/v{instance.version_number}.{suffix}"


class KnowledgeBase(TimeStamped):
    """A corpus that is searched as a unit.

    There is no owner field. This site has one company and one set of staff, and
    a foreign key nothing populates is a column that lies. What the model does
    guarantee is that every retrieval is *already* scoped by knowledge base —
    so introducing tenancy later means adding a column here and a filter in one
    place, not rewriting retrieval.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive knowledge bases keep their documents but are not searched.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Knowledge base"
        verbose_name_plural = "Knowledge bases"

    def __str__(self) -> str:
        return self.name


class Document(TimeStamped):
    """One source document, across all its editions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(
        KnowledgeBase, on_delete=models.CASCADE, related_name="documents"
    )
    name = models.CharField(max_length=200, help_text="What staff call this document.")
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=DocumentState.choices, default=DocumentState.UPLOADED
    )
    # The edition currently answering questions. Null while the first upload is
    # still processing, and left pointing at the previous edition while a new
    # one is being indexed — which is exactly what keeps search working during
    # a re-upload.
    active_version = models.OneToOneField(
        "knowledge.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_documents",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # The control room's default view: one knowledge base, newest first.
            models.Index(fields=["knowledge_base", "-created_at"]),
            # "What is stuck?" — the query an operator runs when something is
            # wrong, across every knowledge base.
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def storage_path(self) -> str:
        """Where the live edition's bytes are, or empty while there is none."""
        return self.active_version.file.name if self.active_version else ""

    def transition_to(self, target: str, *, save: bool = True) -> Document:
        """Move to ``target``, or raise :class:`InvalidTransition`.

        The only supported way to change a document's status. Assigning
        ``status`` directly still works because Django cannot prevent it, but
        nothing in this app does — see ``states.TRANSITIONS`` for the rules.
        """
        check(self.status, target)
        self.status = target
        if save:
            self.save(update_fields=["status", "updated_at"])
        return self

    @transaction.atomic
    def publish_version(self, version: DocumentVersion) -> Document:
        """Make ``version`` the edition that answers questions.

        Both sides move together: a document that says READY while pointing at
        no version, or at a version that is not itself READY, would be a
        document the retrieval layer cannot trust.
        """
        if version.document_id != self.id:
            raise ValueError("That version belongs to a different document.")
        if version.status != DocumentState.READY:
            raise InvalidTransition(version.status, DocumentState.READY)

        self.active_version = version
        if self.status != DocumentState.READY:
            self.transition_to(DocumentState.READY, save=False)
        self.save(update_fields=["active_version", "status", "updated_at"])
        return self


class DocumentVersion(TimeStamped):
    """One immutable edition of a document's content.

    Immutable is the important word. Once bytes are stored under a version
    number they are never replaced — a corrected document is a new version — so
    a chunk in the vector index can always be traced back to the exact content
    it was derived from, and an index built from version 2 cannot be silently
    invalidated by someone re-uploading version 2.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()

    file = models.FileField(upload_to=document_upload_path, max_length=400)
    # SHA-256 of the uploaded bytes. Indexed because it is looked up on every
    # upload to decide whether this is genuinely new content.
    content_hash = models.CharField(max_length=64, db_index=True)
    file_size = models.PositiveBigIntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=DocumentState.choices, default=DocumentState.UPLOADED
    )

    # Filled in by the worker as it learns them; null until then rather than
    # zero, so "not processed yet" and "genuinely empty" stay distinguishable.
    page_count = models.PositiveIntegerField(null=True, blank=True)
    chunk_count = models.PositiveIntegerField(null=True, blank=True)

    # What this edition was indexed *with*. Recorded per version because it
    # decides which collection the vectors live in, and therefore whether this
    # version is still searchable after the service changes embedding model.
    embedding_model = models.CharField(max_length=200, blank=True)
    embedding_model_version = models.CharField(max_length=40, blank=True)
    embedding_dimension = models.PositiveIntegerField(null=True, blank=True)
    collection = models.CharField(
        max_length=200, blank=True, help_text="Vector collection holding this version's chunks."
    )

    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["document", "-version_number"]
        constraints = [
            # The database, not the application, is what makes version numbers
            # unique: two uploads racing would otherwise both read "latest is 2"
            # and both write 3.
            models.UniqueConstraint(
                fields=["document", "version_number"], name="uniq_document_version_number"
            ),
        ]
        indexes = [
            models.Index(fields=["document", "-version_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["content_hash"]),
        ]

    def __str__(self) -> str:
        return f"{self.document.name} v{self.version_number}"

    @property
    def is_active(self) -> bool:
        """Whether this is the edition currently answering questions."""
        return self.document.active_version_id == self.id

    def transition_to(self, target: str, *, save: bool = True) -> DocumentVersion:
        check(self.status, target)
        self.status = target
        if save:
            self.save(update_fields=["status", "updated_at"])
        return self


class JobType(models.TextChoices):
    INGEST = "ingest", "Ingest"
    REINDEX = "reindex", "Reindex"
    DELETE = "delete", "Delete"


class JobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class IngestionJob(TimeStamped):
    """One asynchronous operation against one document version.

    Separate from the version's own status because they answer different
    questions. The version says what is true of the content now; the job says
    what was attempted, when, by which worker, how many times, and what broke.
    Keeping the history means a document that failed three times looks different
    from one that failed once, which is the difference between a bad PDF and a
    flaky provider.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="jobs")
    document_version = models.ForeignKey(
        DocumentVersion, on_delete=models.CASCADE, related_name="jobs", null=True, blank=True
    )

    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.INGEST)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.QUEUED)

    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Whole percent, 0-100.",
    )
    current_stage = models.CharField(
        max_length=20, choices=DocumentState.choices, blank=True,
        help_text="The lifecycle stage the worker last reported.",
    )

    attempt_count = models.PositiveSmallIntegerField(default=0)
    celery_task_id = models.CharField(max_length=155, blank=True, db_index=True)

    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "-created_at"]),
            # The operational sweep: everything queued or running, oldest first.
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_job_type_display()} · {self.document_id} · {self.status}"

    @property
    def duration_seconds(self) -> float | None:
        if not self.started_at or not self.finished_at:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def mark_running(self, stage: str, *, task_id: str = "") -> IngestionJob:
        """Record that a worker has picked this up, or moved to a new stage."""
        fields = ["status", "current_stage", "progress", "updated_at"]
        self.status = JobStatus.RUNNING
        self.current_stage = stage
        self.progress = progress_for(stage)
        if task_id and task_id != self.celery_task_id:
            self.celery_task_id = task_id
            fields.append("celery_task_id")
        if self.started_at is None:
            self.started_at = timezone.now()
            fields.append("started_at")
        self.save(update_fields=fields)
        return self

    def mark_succeeded(self) -> IngestionJob:
        self.status = JobStatus.SUCCEEDED
        self.current_stage = DocumentState.READY
        self.progress = 100
        self.finished_at = timezone.now()
        self.save(
            update_fields=["status", "current_stage", "progress", "finished_at", "updated_at"]
        )
        return self

    def mark_failed(self, code: str, message: str = "") -> IngestionJob:
        self.status = JobStatus.FAILED
        self.error_code = code[:80]
        # Truncated because a provider traceback can be enormous, and the
        # operator needs the first line far more than the last hundred.
        self.error_message = message[:4000]
        self.finished_at = timezone.now()
        self.save(
            update_fields=[
                "status", "error_code", "error_message", "finished_at", "updated_at",
            ]
        )
        return self
