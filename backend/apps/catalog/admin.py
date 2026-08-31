from django.contrib import admin

from .models import (
    Application,
    Component,
    FinishOption,
    LiftImage,
    LiftSpec,
    LiftType,
    LiftVariant,
    SafetyFeature,
)


class LiftImageInline(admin.TabularInline):
    model = LiftImage
    extra = 1
    fields = ["kind", "image", "image_url", "alt", "caption", "order", "is_published"]


class LiftVariantInline(admin.TabularInline):
    model = LiftVariant
    extra = 1


class LiftSpecInline(admin.TabularInline):
    model = LiftSpec
    extra = 1


@admin.register(LiftType)
class LiftTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "tagline", "capacity", "speed", "order", "is_featured", "is_published"]
    list_editable = ["order", "is_featured", "is_published"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["applications", "safety_features"]
    inlines = [LiftImageInline, LiftVariantInline, LiftSpecInline]
    fieldsets = [
        ("Identity", {"fields": ["name", "slug", "short_name", "eyebrow", "tagline", "accent"]}),
        ("Copy", {"fields": ["summary", "overview"]}),
        ("Headline specs", {"fields": ["speed", "capacity", "stops", "drive"]}),
        ("Selector ranges", {"fields": [
            ("min_floors", "max_floors"), ("min_persons", "max_persons"),
            "pit_depth", "headroom", "shaft_footprint", "machine_room",
        ]}),
        ("Media", {"fields": ["hero_image_url", "hero_video_url"]}),
        ("Relations", {"fields": ["applications", "safety_features"]}),
        ("Publishing", {"fields": ["order", "is_featured", "is_published"]}),
    ]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["name", "group", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SafetyFeature)
class SafetyFeatureAdmin(admin.ModelAdmin):
    list_display = ["name", "standard", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FinishOption)
class FinishOptionAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "swatch_hex", "tier", "order", "is_published"]
    list_editable = ["order", "is_published"]
    list_filter = ["category", "tier"]


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ["index", "name", "supplier", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ("name",)}
