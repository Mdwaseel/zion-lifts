from django.db import models

from apps.catalog.models import LiftType
from apps.core.models import Ordered, TimeStamped


class ProjectCategory(Ordered):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=220, blank=True)

    class Meta(Ordered.Meta):
        verbose_name_plural = "Project categories"

    def __str__(self):
        return self.name


class Project(Ordered, TimeStamped):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=140)
    client = models.CharField(max_length=140, blank=True)
    location = models.CharField(max_length=140, default="Hyderabad, Telangana")
    year = models.PositiveIntegerField(null=True, blank=True)
    category = models.ForeignKey(
        ProjectCategory, on_delete=models.SET_NULL, null=True, related_name="projects"
    )
    lift_type = models.ForeignKey(
        LiftType, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects"
    )

    statement = models.CharField(
        max_length=220, blank=True, help_text="One-line architecture statement under the hero."
    )
    summary = models.TextField(blank=True)
    challenge = models.TextField(blank=True)
    solution = models.TextField(blank=True)
    result = models.TextField(blank=True)

    # metadata strip on the case-study page
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

    def __str__(self):
        return self.name


class ProjectImage(Ordered):
    STAGES = [
        ("site", "Site"),
        ("installation", "Installation"),
        ("interior", "Interior"),
        ("completion", "Completion"),
        ("detail", "Detail"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    stage = models.CharField(max_length=20, choices=STAGES, default="interior")
    image = models.ImageField(upload_to="projects/", blank=True)
    image_url = models.CharField(max_length=300, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    alt = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.project.name} - {self.stage}"
