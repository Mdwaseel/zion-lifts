from django.contrib import admin

from .models import Certification, Office, Partner, SiteSettings, Stat


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Identity", {"fields": ["company_name", "tagline", "statement"]}),
        ("Contact", {"fields": ["phone", "phone_service", "whatsapp", "email", "email_service"]}),
        ("Proof", {"fields": ["founded_year", "installations", "team_size"]}),
        ("Location", {"fields": ["city", "country"]}),
        ("Social", {"fields": ["instagram", "linkedin", "youtube"]}),
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "city", "phone", "order", "is_published"]
    list_editable = ["order", "is_published"]
    list_filter = ["kind", "city"]


@admin.register(Stat)
class StatAdmin(admin.ModelAdmin):
    list_display = ["value", "label", "group", "order", "is_published"]
    list_editable = ["order", "is_published"]
    list_filter = ["group"]


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "role", "component", "order", "is_published"]
    list_editable = ["order", "is_published"]
    list_filter = ["role"]


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ["name", "issuer", "reference", "order", "is_published"]
    list_editable = ["order", "is_published"]
