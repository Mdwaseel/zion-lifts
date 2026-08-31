from django.contrib import admin

from .models import (
    FAQ,
    Award,
    FAQCategory,
    GalleryItem,
    JournalCategory,
    JournalPost,
    LegalClause,
    LegalDocument,
    Milestone,
    ServicePillar,
    TeamMember,
    Testimonial,
)


class FAQInline(admin.StackedInline):
    model = FAQ
    extra = 1


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FAQInline]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ["question", "category", "scope", "order", "is_published"]
    list_editable = ["order", "is_published"]
    list_filter = ["category", "scope"]
    search_fields = ["question", "answer"]


@admin.register(JournalPost)
class JournalPostAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "published_at", "is_featured", "is_published"]
    list_editable = ["is_featured", "is_published"]
    list_filter = ["category", "is_featured"]
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ["title", "excerpt"]


@admin.register(JournalCategory)
class JournalCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["name", "organisation", "project", "is_featured", "order", "is_published"]
    list_editable = ["is_featured", "order", "is_published"]


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ["year", "title", "order", "is_published"]
    list_editable = ["order", "is_published"]


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ["name", "role", "department", "is_leadership", "order", "is_published"]
    list_editable = ["is_leadership", "order", "is_published"]
    list_filter = ["department", "is_leadership"]


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ["name", "organisation", "year", "order", "is_published"]
    list_editable = ["order", "is_published"]


@admin.register(ServicePillar)
class ServicePillarAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ["__str__", "category", "meta", "is_featured", "order", "is_published"]
    list_editable = ["is_featured", "order", "is_published"]
    list_filter = ["category", "is_featured"]


class LegalClauseInline(admin.StackedInline):
    model = LegalClause
    extra = 1


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "effective_date"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LegalClauseInline]
