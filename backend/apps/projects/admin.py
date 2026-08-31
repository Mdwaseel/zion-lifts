from django.contrib import admin

from .models import Project, ProjectCategory, ProjectImage


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "name", "location", "category", "lift_type", "year",
        "is_featured", "order", "is_published",
    ]
    list_editable = ["is_featured", "order", "is_published"]
    list_filter = ["category", "lift_type", "year"]
    search_fields = ["name", "client", "location"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProjectImageInline]
    fieldsets = [
        ("Identity", {
            "fields": ["name", "slug", "client", "location", "year", "category", "lift_type"]
        }),
        ("Story", {"fields": ["statement", "summary", "challenge", "solution", "result"]}),
        ("Specification", {"fields": ["system", "capacity", "stops", "door", "drive", "scope"]}),
        ("Media", {
            "fields": ["hero_image_url", "hero_video_url", "loop_video_url",
                       "poster_url", "is_portrait"]
        }),
        ("Publishing", {"fields": ["order", "is_featured", "is_published"]}),
    ]


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ("name",)}
