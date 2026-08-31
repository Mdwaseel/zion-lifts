from django.db import models
from django.utils.text import slugify

from apps.core.models import Ordered, TimeStamped


class Application(Ordered):
    """Building context a lift is suited to — villa, hotel, hospital, …"""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    group = models.CharField(
        max_length=40,
        default="residential",
        help_text="residential / commercial / institutional / industrial",
    )
    description = models.CharField(max_length=220, blank=True)
    image_url = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name


class SafetyFeature(Ordered):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    headline = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    test_procedure = models.TextField(
        blank=True, help_text="What the safety-lab section describes for this test."
    )
    standard = models.CharField(max_length=120, blank=True)
    media_url = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name


class FinishOption(Ordered):
    """Swatches driving the cabin configurator."""

    CATEGORIES = [
        ("material", "Wall material"),
        ("floor", "Flooring"),
        ("light", "Lighting"),
        ("door", "Door"),
        ("control", "Control panel"),
        ("handrail", "Handrail"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORIES, db_index=True)
    slug = models.SlugField()
    name = models.CharField(max_length=90)
    description = models.CharField(max_length=200, blank=True)
    swatch_hex = models.CharField(max_length=9, default="#C9B79A")
    swatch_hex_2 = models.CharField(
        max_length=9, blank=True, help_text="Second stop for a two-tone swatch."
    )
    texture = models.ImageField(upload_to="finishes/", blank=True)
    texture_url = models.CharField(max_length=300, blank=True)
    tier = models.CharField(max_length=20, default="standard")

    class Meta(Ordered.Meta):
        unique_together = [("category", "slug")]

    def __str__(self):
        return f"{self.get_category_display()} — {self.name}"


class LiftType(Ordered, TimeStamped):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=90)
    short_name = models.CharField(max_length=40, blank=True)
    eyebrow = models.CharField(max_length=60, blank=True)
    tagline = models.CharField(max_length=180)
    summary = models.TextField(help_text="One paragraph — used on cards and the index grid.")
    overview = models.TextField(blank=True, help_text="Two paragraphs for the product page.")

    # headline specs, shown as the four key numbers under the product hero
    speed = models.CharField(max_length=40, blank=True)
    capacity = models.CharField(max_length=60, blank=True)
    stops = models.CharField(max_length=40, blank=True)
    drive = models.CharField(max_length=80, blank=True)

    # selector inputs used by the lift finder
    min_floors = models.PositiveIntegerField(default=2)
    max_floors = models.PositiveIntegerField(default=12)
    min_persons = models.PositiveIntegerField(default=3)
    max_persons = models.PositiveIntegerField(default=13)
    pit_depth = models.CharField(max_length=40, blank=True)
    headroom = models.CharField(max_length=40, blank=True)
    shaft_footprint = models.CharField(max_length=60, blank=True)
    machine_room = models.CharField(max_length=40, blank=True, default="Not required")

    hero_image_url = models.CharField(max_length=300, blank=True)
    hero_video_url = models.CharField(max_length=300, blank=True)
    accent = models.CharField(max_length=9, default="#048D8E")

    applications = models.ManyToManyField(Application, blank=True, related_name="lift_types")
    safety_features = models.ManyToManyField(SafetyFeature, blank=True, related_name="lift_types")
    is_featured = models.BooleanField(default=False)

    class Meta(Ordered.Meta):
        verbose_name = "Lift type"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.short_name:
            self.short_name = self.name
        super().save(*args, **kwargs)


class LiftImage(Ordered):
    KINDS = [
        ("hero", "Hero"),
        ("gallery", "Gallery"),
        ("cabin", "Cabin"),
        ("detail", "Detail"),
        ("diagram", "Diagram"),
    ]

    lift_type = models.ForeignKey(LiftType, on_delete=models.CASCADE, related_name="images")
    kind = models.CharField(max_length=20, choices=KINDS, default="gallery")
    image = models.ImageField(upload_to="lifts/", blank=True)
    image_url = models.CharField(max_length=300, blank=True)
    alt = models.CharField(max_length=200, blank=True)
    caption = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.lift_type.name} — {self.kind}"


class LiftVariant(Ordered):
    lift_type = models.ForeignKey(LiftType, on_delete=models.CASCADE, related_name="variants")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=90)
    description = models.CharField(max_length=240, blank=True)
    capacity = models.CharField(max_length=60, blank=True)
    persons = models.CharField(max_length=30, blank=True)
    speed = models.CharField(max_length=40, blank=True)
    shaft = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return f"{self.lift_type.short_name} {self.code}"


class LiftSpec(Ordered):
    """Free-form spec rows grouped into tables on the product page."""

    lift_type = models.ForeignKey(LiftType, on_delete=models.CASCADE, related_name="specs")
    group = models.CharField(max_length=60, default="Dimensions")
    label = models.CharField(max_length=90)
    value = models.CharField(max_length=140)
    note = models.CharField(max_length=200, blank=True)

    class Meta(Ordered.Meta):
        ordering = ["group", "order", "pk"]

    def __str__(self):
        return f"{self.label}: {self.value}"


class Component(Ordered):
    """The exploded-view callouts in 'Enter the machine'."""

    slug = models.SlugField(unique=True)
    index = models.CharField(max_length=4, default="01")
    name = models.CharField(max_length=90)
    description = models.TextField(blank=True)
    detail = models.CharField(max_length=200, blank=True)
    supplier = models.CharField(max_length=90, blank=True)

    def __str__(self):
        return f"{self.index} {self.name}"
