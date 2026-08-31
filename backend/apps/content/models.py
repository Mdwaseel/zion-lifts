from django.db import models
from django.utils import timezone

from apps.core.models import Ordered, TimeStamped


# --------------------------------------------------------------------------- FAQ
class FAQCategory(Ordered):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=90)
    description = models.CharField(max_length=200, blank=True)

    class Meta(Ordered.Meta):
        verbose_name = "FAQ category"
        verbose_name_plural = "FAQ categories"

    def __str__(self):
        return self.name


class FAQ(Ordered):
    category = models.ForeignKey(
        FAQCategory, on_delete=models.CASCADE, related_name="questions"
    )
    question = models.CharField(max_length=240)
    answer = models.TextField()
    link_label = models.CharField(
        max_length=120, blank=True, help_text='e.g. "Explore Home Elevators"'
    )
    link_url = models.CharField(max_length=200, blank=True)
    scope = models.CharField(
        max_length=30,
        default="general",
        help_text="general / contact — contact-scoped questions only show on /contact.",
    )

    class Meta(Ordered.Meta):
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


# ----------------------------------------------------------------------- Journal
class JournalCategory(Ordered):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=90)

    class Meta(Ordered.Meta):
        verbose_name_plural = "Journal categories"

    def __str__(self):
        return self.name


class JournalPost(Ordered, TimeStamped):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    category = models.ForeignKey(
        JournalCategory, on_delete=models.SET_NULL, null=True, related_name="posts"
    )
    excerpt = models.TextField(blank=True)
    body = models.TextField(
        blank=True,
        help_text="Markdown-ish: '## ' starts a section, '> ' a pull quote, blank line splits paragraphs.",
    )
    hero_image_url = models.CharField(max_length=300, blank=True)
    read_minutes = models.PositiveIntegerField(default=5)
    published_at = models.DateTimeField(default=timezone.now)
    is_featured = models.BooleanField(default=False)

    class Meta(Ordered.Meta):
        ordering = ["-published_at", "order"]

    def __str__(self):
        return self.title


# ------------------------------------------------------------------ Testimonials
class Testimonial(Ordered):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    organisation = models.CharField(max_length=140, blank=True)
    location = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="testimonials",
    )
    video_url = models.CharField(max_length=300, blank=True)
    poster_url = models.CharField(max_length=300, blank=True)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.organisation}" if self.organisation else self.name


# --------------------------------------------------------------------- The story
class Milestone(Ordered):
    year = models.CharField(max_length=12)
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=300, blank=True)

    class Meta(Ordered.Meta):
        ordering = ["order", "year"]

    def __str__(self):
        return f"{self.year} - {self.title}"


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

    def __str__(self):
        return f"{self.name} - {self.role}"


class Award(Ordered):
    name = models.CharField(max_length=180)
    organisation = models.CharField(max_length=160, blank=True)
    year = models.CharField(max_length=12, blank=True)
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name


class ServicePillar(Ordered):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    detail = models.CharField(max_length=200, blank=True)
    icon = models.CharField(
        max_length=30, default="wrench", help_text="Key into the front-end icon set."
    )

    def __str__(self):
        return self.name


# ----------------------------------------------------------------------- Gallery
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
        max_length=200, blank=True, help_text='e.g. "Home Elevator - Private Residence - Hyderabad"'
    )
    image = models.ImageField(upload_to="gallery/", blank=True)
    image_url = models.CharField(max_length=300, blank=True)
    width = models.PositiveIntegerField(default=1600)
    height = models.PositiveIntegerField(default=900)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="gallery_items",
    )
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title or f"Gallery #{self.pk}"

    @property
    def aspect(self):
        return round(self.width / self.height, 4) if self.height else 1.0


# ------------------------------------------------------------------------- Legal
class LegalDocument(TimeStamped):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=140)
    intro = models.TextField(blank=True)
    effective_date = models.DateField(default=timezone.localdate)

    def __str__(self):
        return self.title


class LegalClause(Ordered):
    document = models.ForeignKey(
        LegalDocument, on_delete=models.CASCADE, related_name="clauses"
    )
    heading = models.CharField(max_length=180)
    body = models.TextField()

    def __str__(self):
        return self.heading
