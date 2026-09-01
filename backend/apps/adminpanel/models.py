"""Every model the site owns, in the app that edits them.

This app used to declare no models of its own: the control room was a generic
CRUD layer pointed at ``catalog``, ``projects``, ``content``, ``core`` and
``enquiries``. That split meant a single screen in the panel was assembled from
several tables in several apps, and the panel could not decide the shape of the
data it existed to edit.

The models moved here, and were consolidated on the way. Two rules did the
consolidating:

**A category is a field, not a table.** ``ProjectCategory``, ``JournalCategory``
and ``FAQCategory`` were each a slug and a name maintained by hand, joined to
exactly one parent, and used by the front end only to draw a filter chip. They
are now ``choices`` on the parent, and the endpoints that listed them derive the
list — with live counts — from the rows themselves. A category can no longer be
orphaned, misspelt in two places, or exist with nothing in it.

**A child row that is only ever read with its parent is JSON on the parent.**
A project's photographs, a lift's images, variants and spec rows and an
enquiry's attachments are never queried on their own, never sorted
independently, and never joined to anything else — they are lists that belong to
one record and are fetched with it. They are ``JSONField`` lists now, so editing
a project is one form and one save rather than a parent form plus a table of
children.

A third rule arrived later, and it removed six models rather than merging them:
**content that never changes between deploys does not need a database.** The
FAQ, the company timeline, the certifications, the service pillars, the stat
rows and the three policy pages were each a table, a migration, a serializer, an
endpoint and an admin form rendering text that nobody had edited since it was
seeded. They are now plain modules in ``frontend/src/data/``, versioned with the
markup that renders them and present on the first paint. Migration 0004 drops
what is left.

What did *not* collapse: ``Application``, ``SafetyFeature``, ``Finish`` and the
organisation models are genuinely shared or independently listed by the public
API, so they stay addressable rows. Everything still here is something an
operator is expected to change without a deploy.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


# --------------------------------------------------------------------- bases
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


def choice_label(choices: list[tuple[str, str]], value: str) -> str:
    """The display name for a stored slug, or the slug itself if unknown.

    Falling back to the raw value rather than an empty string matters: a row
    written before a choice was renamed still renders something a person can
    read, instead of a blank filter chip.
    """
    return dict(choices).get(value, value)


# ===================================================================
# Catalogue
# ===================================================================
class Application(Ordered):
    """A building context a lift suits — villa, hotel, hospital, …

    Kept as its own table rather than folded into ``Lift``: /api/applications/
    lists it on its own for the range page's filter, and the same eight rows are
    shared by every lift.
    """

    GROUPS = [
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("institutional", "Institutional"),
        ("industrial", "Industrial"),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    group = models.CharField(max_length=40, choices=GROUPS, default="residential")
    description = models.CharField(max_length=220, blank=True)
    image_url = models.CharField(max_length=300, blank=True)

    def __str__(self) -> str:
        return self.name


class SafetyFeature(Ordered):
    """One protection, and how it is proven. Listed on its own by the home page."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    headline = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    test_procedure = models.TextField(
        blank=True, help_text="What the safety-lab section describes for this test."
    )
    standard = models.CharField(max_length=120, blank=True)
    media_url = models.CharField(max_length=300, blank=True)

    def __str__(self) -> str:
        return self.name


class Finish(Ordered):
    """A swatch in the cabin configurator."""

    CATEGORIES = [
        ("material", "Wall material"),
        ("floor", "Flooring"),
        ("light", "Lighting"),
        ("door", "Door"),
        ("control", "Control panel"),
        ("handrail", "Handrail"),
    ]
    TIERS = [
        ("standard", "Standard"),
        ("premium", "Premium"),
        ("signature", "Signature"),
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
    tier = models.CharField(max_length=20, choices=TIERS, default="standard")

    class Meta(Ordered.Meta):
        unique_together = [("category", "slug")]

    def __str__(self) -> str:
        return f"{self.get_category_display()} — {self.name}"


class Component(Ordered):
    """An exploded-view callout in 'Enter the machine'."""

    slug = models.SlugField(unique=True)
    index = models.CharField(max_length=4, default="01")
    name = models.CharField(max_length=90)
    description = models.TextField(blank=True)
    detail = models.CharField(max_length=200, blank=True)
    supplier = models.CharField(max_length=90, blank=True)

    def __str__(self) -> str:
        return f"{self.index} {self.name}"


class Lift(Ordered, TimeStamped):
    """One lift in the range — the whole product page in a single row.

    ``images``, ``variants`` and ``specs`` were three tables hanging off this
    one. Nothing ever asked for a lift image without asking for its lift, so
    they are lists here: editing a lift is one form, and the detail endpoint is
    one query instead of four.
    """

    IMAGE_KINDS = ["hero", "gallery", "cabin", "detail", "diagram"]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=90)
    short_name = models.CharField(max_length=40, blank=True)
    eyebrow = models.CharField(max_length=60, blank=True)
    tagline = models.CharField(max_length=180)
    summary = models.TextField(help_text="One paragraph — used on cards and the index grid.")
    overview = models.TextField(blank=True, help_text="Two paragraphs for the product page.")

    # the four headline numbers under the product hero
    speed = models.CharField(max_length=40, blank=True)
    capacity = models.CharField(max_length=60, blank=True)
    stops = models.CharField(max_length=40, blank=True)
    drive = models.CharField(max_length=80, blank=True)

    # what the lift finder filters on
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

    images = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"kind": "gallery", "src": "…", "alt": "…", "caption": "…"}]',
    )
    variants = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"code": "ZL-6", "name": "…", "description": "…", "capacity": "…", '
        '"persons": "…", "speed": "…", "shaft": "…"}]',
    )
    specs = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"group": "Dimensions", "label": "…", "value": "…", "note": "…"}]',
    )

    applications = models.ManyToManyField(Application, blank=True, related_name="lifts")
    safety_features = models.ManyToManyField(SafetyFeature, blank=True, related_name="lifts")
    is_featured = models.BooleanField(default=False)

    class Meta(Ordered.Meta):
        verbose_name = "Lift"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.short_name:
            self.short_name = self.name
        super().save(*args, **kwargs)


# ===================================================================
# Projects
# ===================================================================
class Project(Ordered, TimeStamped):
    """One completed installation, whole.

    Was three models. ``ProjectCategory`` is now ``category`` — the six
    buildings types were never edited, only chosen — and ``ProjectImage`` is the
    ``images`` list, because the case-study page reads every photograph of a
    project at once and nothing else ever reads one.
    """

    CATEGORIES = [
        ("residential", "Residential"),
        ("hospitality", "Hospitality"),
        ("healthcare", "Healthcare"),
        ("commercial", "Commercial"),
        ("institutional", "Institutional"),
        ("industrial", "Industrial"),
    ]
    # The blurb each category carried when it was a table. Kept beside the
    # choices so /api/project-categories/ can still describe itself.
    CATEGORY_DESCRIPTIONS = {
        "residential": "Villas, private homes and apartment buildings.",
        "hospitality": "Restaurants, cafes and hotels.",
        "healthcare": "Hospitals, clinics and diagnostic centres.",
        "commercial": "Offices, retail and mixed-use buildings.",
        "institutional": "Government, education and public buildings.",
        "industrial": "Factories, warehouses and parking structures.",
    }
    IMAGE_STAGES = ["site", "installation", "interior", "completion", "detail"]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=140)
    client = models.CharField(max_length=140, blank=True)
    location = models.CharField(max_length=140, default="Hyderabad, Telangana")
    year = models.PositiveIntegerField(null=True, blank=True)
    category = models.CharField(
        max_length=30, choices=CATEGORIES, default="residential", db_index=True
    )
    lift = models.ForeignKey(
        Lift, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects"
    )

    statement = models.CharField(
        max_length=220, blank=True, help_text="One-line architecture statement under the hero."
    )
    summary = models.TextField(blank=True)
    challenge = models.TextField(blank=True)
    solution = models.TextField(blank=True)
    result = models.TextField(blank=True)

    # the metadata strip on the case-study page
    system = models.CharField(max_length=90, blank=True)
    capacity = models.CharField(max_length=60, blank=True)
    stops = models.CharField(max_length=30, blank=True)
    door = models.CharField(max_length=90, blank=True)
    drive = models.CharField(max_length=90, blank=True)
    scope = models.CharField(max_length=200, blank=True)

    hero_image_url = models.CharField(max_length=300, blank=True)
    hero_video_url = models.CharField(max_length=300, blank=True)
    loop_video_url = models.CharField(max_length=300, blank=True)
    poster_url = models.CharField(max_length=300, blank=True)
    is_portrait = models.BooleanField(
        default=False, help_text="Tick when the project film is shot vertically."
    )
    is_featured = models.BooleanField(default=False)

    images = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"stage": "interior", "src": "…", "caption": "…", "alt": "…"}]',
    )

    def __str__(self) -> str:
        return self.name

    @property
    def category_name(self) -> str:
        return choice_label(self.CATEGORIES, self.category)


# ===================================================================
# Blogs
# ===================================================================
class BlogPost(Ordered, TimeStamped):
    """A journal article. ``JournalCategory`` is a field here, not a table."""

    CATEGORIES = [
        ("elevators", "Elevators"),
        ("architecture", "Architecture"),
        ("engineering", "Engineering"),
        ("safety", "Safety"),
        ("maintenance", "Maintenance"),
        ("projects", "Projects"),
    ]

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30, choices=CATEGORIES, default="engineering", db_index=True
    )
    excerpt = models.TextField(blank=True)
    body = models.TextField(
        blank=True,
        help_text="Markdown-ish: '## ' starts a section, '> ' a pull quote, "
        "a blank line splits paragraphs.",
    )
    hero_image_url = models.CharField(max_length=300, blank=True)
    read_minutes = models.PositiveIntegerField(default=5)
    published_at = models.DateTimeField(default=timezone.now)
    is_featured = models.BooleanField(default=False)

    class Meta(Ordered.Meta):
        ordering = ["-published_at", "order"]
        verbose_name = "Blog post"

    def __str__(self) -> str:
        return self.title

    @property
    def category_name(self) -> str:
        return choice_label(self.CATEGORIES, self.category)


# ===================================================================
# Editorial
# ===================================================================
class Testimonial(Ordered):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    organisation = models.CharField(max_length=140, blank=True)
    location = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="testimonials"
    )
    video_url = models.CharField(max_length=300, blank=True)
    poster_url = models.CharField(max_length=300, blank=True)
    is_featured = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.name} - {self.organisation}" if self.organisation else self.name


class GalleryItem(Ordered):
    CATEGORIES = [
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("institutional", "Institutional"),
        ("interiors", "Interiors"),
        ("installation", "Installation"),
        ("factory", "Factory"),
        ("awards", "Awards"),
        ("people", "People"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORIES, default="interiors")
    title = models.CharField(max_length=160, blank=True)
    meta = models.CharField(
        max_length=200,
        blank=True,
        help_text='e.g. "Home Elevator - Private Residence - Hyderabad"',
    )
    image = models.ImageField(upload_to="gallery/", blank=True)
    image_url = models.CharField(max_length=300, blank=True)
    width = models.PositiveIntegerField(default=1600)
    height = models.PositiveIntegerField(default=900)
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="gallery_items"
    )
    is_featured = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title or f"Gallery #{self.pk}"

    @property
    def aspect(self) -> float:
        return round(self.width / self.height, 4) if self.height else 1.0


class TeamMember(Ordered):
    DEPARTMENTS = [
        ("leadership", "Leadership"),
        ("engineering", "Engineering"),
        ("manufacturing", "Manufacturing"),
        ("installation", "Installation & service"),
        ("design", "Design"),
    ]

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    department = models.CharField(max_length=30, choices=DEPARTMENTS, default="engineering")
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="team/", blank=True)
    photo_url = models.CharField(max_length=300, blank=True)
    is_leadership = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.name} - {self.role}"


class Award(Ordered):
    name = models.CharField(max_length=180)
    organisation = models.CharField(max_length=160, blank=True)
    year = models.CharField(max_length=12, blank=True)
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=300, blank=True)

    def __str__(self) -> str:
        return self.name


# ===================================================================
# Organisation
# ===================================================================
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

    def __str__(self) -> str:
        return self.company_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - guard only
        raise ValidationError("Site settings cannot be deleted.")

    @classmethod
    def load(cls) -> "SiteSettings":
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

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()})"


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

    def __str__(self) -> str:
        return self.name


# ===================================================================
# Inbox
# ===================================================================
class Enquiry(TimeStamped):
    """A new-installation enquiry from the three-step form.

    One model, not two. ``EnquiryAttachment`` existed to hold a handful of
    drawings that are only ever listed with the enquiry they arrived on; they
    are now the ``attachments`` list, each entry recording the stored path, the
    name the customer's file had, and its size.

    The customer's own answers are never edited from the panel — see
    ``resources.py``, which marks them read-only. Staff add ``status`` and
    ``internal_notes`` and nothing else, so the record of what was asked for
    stays the record of what was asked for.
    """

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
    INSTALLATION_KINDS = [
        ("new", "New installation"),
        ("replacement", "Replacement"),
        ("modernisation", "Modernisation"),
    ]
    STATUSES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("quoted", "Quoted"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("spam", "Spam"),
    ]

    # step 1 — the project
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPES, blank=True)
    project_stage = models.CharField(max_length=30, choices=STAGES, blank=True)
    location = models.CharField(max_length=160, blank=True)
    floors = models.CharField(max_length=30, blank=True)

    # step 2 — the configuration
    lift = models.ForeignKey(
        Lift, on_delete=models.SET_NULL, null=True, blank=True, related_name="enquiries"
    )
    lift_type_note = models.CharField(
        max_length=60, blank=True, help_text='Set to "not-sure" when no type was chosen.'
    )
    capacity = models.CharField(max_length=60, blank=True)
    stops = models.CharField(max_length=30, blank=True)
    installation_kind = models.CharField(
        max_length=30, choices=INSTALLATION_KINDS, blank=True
    )
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Cabin configurator selections carried over from the product page.",
    )

    # step 3 — the brief
    name = models.CharField(max_length=140)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    organisation = models.CharField(max_length=160, blank=True)
    message = models.TextField(blank=True)
    consent = models.BooleanField(default=False)
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"name": "plan.pdf", "path": "enquiries/…", "size": 81234}]',
    )

    source_path = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="new", db_index=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Enquiries"

    def __str__(self) -> str:
        return f"{self.name} - {self.created_at:%d %b %Y}"

    @property
    def reference(self) -> str:
        return f"ZL-{self.created_at:%y%m}-{self.pk:04d}"

    @property
    def attachment_count(self) -> int:
        return len(self.attachments or [])


class ServiceRequest(TimeStamped):
    """An existing owner asking for maintenance, a call-out, or modernisation."""

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
    status = models.CharField(max_length=20, choices=STATUSES, default="new", db_index=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} - {self.name}"

    @property
    def reference(self) -> str:
        return f"SR-{self.created_at:%y%m}-{self.pk:04d}"
