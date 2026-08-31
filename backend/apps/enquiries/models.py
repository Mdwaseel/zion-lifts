from django.db import models

from apps.core.models import TimeStamped


class Enquiry(TimeStamped):
    """A new-installation project enquiry from the 3-step form."""

    PROPERTY_TYPES = [
        ("villa", "Villa / independent house"),
        ("apartment", "Apartment building"),
        ("office", "Office / commercial"),
        ("hotel", "Hotel / hospitality"),
        ("hospital", "Hospital / healthcare"),
        ("institutional", "Institutional / government"),
        ("industrial", "Industrial / warehouse"),
        ("retail", "Retail"),
        ("other", "Other"),
    ]
    STAGES = [
        ("planning", "Planning / design"),
        ("construction", "Under construction"),
        ("ready", "Building ready"),
        ("replacement", "Replacing an existing lift"),
    ]
    STATUSES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("quoted", "Quoted"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("spam", "Spam"),
    ]

    # step 1 — project
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPES, blank=True)
    project_stage = models.CharField(max_length=30, choices=STAGES, blank=True)
    location = models.CharField(max_length=160, blank=True)
    floors = models.CharField(max_length=30, blank=True)

    # step 2 — configuration
    lift_type = models.ForeignKey(
        "catalog.LiftType", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="enquiries",
    )
    lift_type_note = models.CharField(
        max_length=60, blank=True, help_text='Set to "not-sure" when no type was chosen.'
    )
    capacity = models.CharField(max_length=60, blank=True)
    stops = models.CharField(max_length=30, blank=True)
    installation_kind = models.CharField(max_length=30, blank=True)
    configuration = models.JSONField(
        default=dict, blank=True,
        help_text="Cabin configurator selections carried over from the product page.",
    )

    # step 3 — brief
    name = models.CharField(max_length=140)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    organisation = models.CharField(max_length=160, blank=True)
    message = models.TextField(blank=True)
    consent = models.BooleanField(default=False)

    source_path = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="new")
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Enquiries"

    def __str__(self):
        return f"{self.name} - {self.created_at:%d %b %Y}"


class EnquiryAttachment(models.Model):
    enquiry = models.ForeignKey(
        Enquiry, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="enquiries/%Y/%m/")
    original_name = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name or self.file.name


class ServiceRequest(TimeStamped):
    """An existing owner asking for maintenance, a breakdown call-out, or modernisation."""

    KINDS = [
        ("maintenance", "Maintenance / AMC"),
        ("breakdown", "Breakdown support"),
        ("modernisation", "Modernisation"),
        ("spares", "Spare parts"),
    ]
    URGENCIES = [
        ("routine", "Routine"),
        ("soon", "Within a few days"),
        ("urgent", "Urgent - lift is down"),
    ]
    STATUSES = [
        ("new", "New"),
        ("scheduled", "Scheduled"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    kind = models.CharField(max_length=20, choices=KINDS, default="maintenance")
    urgency = models.CharField(max_length=20, choices=URGENCIES, default="routine")
    name = models.CharField(max_length=140)
    phone = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    site_name = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=160, blank=True)
    lift_reference = models.CharField(max_length=90, blank=True)
    message = models.TextField(blank=True)
    consent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUSES, default="new")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} - {self.name}"
