from django.core.exceptions import ValidationError
from django.db import models


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Ordered(models.Model):
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class SiteSettings(TimeStamped):
    """Singleton — the handful of values that appear on every page."""

    company_name = models.CharField(max_length=120, default="Zion Lifts")
    tagline = models.CharField(max_length=200, default="Engineered to rise.")
    statement = models.TextField(
        default="Helping people move the right way — safer, quieter, better.",
        help_text="Used in the footer and as the closing line on About.",
    )
    phone = models.CharField(max_length=40, default="+91 91000 00000")
    phone_service = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    email = models.EmailField(default="info@zionlifts.com")
    email_service = models.EmailField(blank=True)
    founded_year = models.PositiveIntegerField(default=2012)
    installations = models.PositiveIntegerField(default=1750)
    team_size = models.CharField(max_length=20, default="95–100")
    city = models.CharField(max_length=80, default="Hyderabad")
    country = models.CharField(max_length=80, default="India")
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    youtube = models.URLField(blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - guard only
        raise ValidationError("Site settings cannot be deleted.")

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Office(Ordered, TimeStamped):
    HEAD = "head_office"
    FACTORY = "factory"
    KINDS = [(HEAD, "Head office"), (FACTORY, "Factory")]

    kind = models.CharField(max_length=20, choices=KINDS, default=HEAD)
    name = models.CharField(max_length=120)
    address = models.TextField()
    locality = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80, default="Hyderabad")
    state = models.CharField(max_length=80, default="Telangana")
    postcode = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    hours = models.CharField(max_length=160, blank=True)
    note = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    map_embed_url = models.URLField(blank=True, max_length=600)
    directions_url = models.URLField(blank=True, max_length=600)

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"


class Stat(Ordered):
    """Small numeric proof points — About header, Projects header."""

    GROUPS = [("about", "About"), ("projects", "Projects"), ("home", "Home")]

    group = models.CharField(max_length=20, choices=GROUPS, default="about")
    value = models.CharField(max_length=20)
    label = models.CharField(max_length=80)
    caption = models.CharField(max_length=140, blank=True)
    count_from = models.CharField(
        max_length=20, blank=True, help_text="Set to animate a count-up, e.g. 0"
    )

    def __str__(self):
        return f"{self.value} {self.label}"


class Partner(Ordered):
    ROLES = [
        ("drive", "Drive"),
        ("motor", "Motor"),
        ("controller", "Controller"),
        ("door", "Door"),
        ("safety", "Safety"),
        ("cabin", "Cabin"),
    ]

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=ROLES, default="drive")
    component = models.CharField(max_length=120, blank=True)
    logo = models.ImageField(upload_to="partners/", blank=True)
    logo_url = models.CharField(max_length=300, blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Certification(Ordered):
    name = models.CharField(max_length=140)
    issuer = models.CharField(max_length=140, blank=True)
    reference = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    certificate = models.FileField(upload_to="certificates/", blank=True)
    certificate_url = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name
