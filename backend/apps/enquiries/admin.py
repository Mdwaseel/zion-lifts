from django.contrib import admin
from django.utils.html import format_html

from .models import Enquiry, EnquiryAttachment, ServiceRequest


class EnquiryAttachmentInline(admin.TabularInline):
    model = EnquiryAttachment
    extra = 0
    readonly_fields = ["original_name", "uploaded_at"]


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = [
        "name", "organisation", "phone", "property_type",
        "lift_type", "location", "status", "created_at",
    ]
    list_filter = ["status", "property_type", "project_stage", "lift_type", "created_at"]
    search_fields = ["name", "email", "phone", "organisation", "location", "message"]
    list_editable = ["status"]
    date_hierarchy = "created_at"
    inlines = [EnquiryAttachmentInline]
    readonly_fields = ["created_at", "updated_at", "configuration_pretty", "source_path"]
    fieldsets = [
        ("Contact", {"fields": ["name", "phone", "email", "organisation", "consent"]}),
        ("Project", {"fields": ["property_type", "project_stage", "location", "floors"]}),
        ("Configuration", {
            "fields": ["lift_type", "lift_type_note", "capacity", "stops",
                       "installation_kind", "configuration_pretty"]
        }),
        ("Brief", {"fields": ["message"]}),
        ("Pipeline", {"fields": ["status", "internal_notes"]}),
        ("Meta", {"fields": ["source_path", "created_at", "updated_at"]}),
    ]

    @admin.display(description="Cabin configuration")
    def configuration_pretty(self, obj):
        if not obj.configuration:
            return "-"
        rows = "".join(
            f"<tr><th style='text-align:left;padding-right:14px'>{k}</th><td>{v}</td></tr>"
            for k, v in obj.configuration.items()
        )
        return format_html("<table>{}</table>", format_html(rows))


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "urgency", "site_name", "phone", "status", "created_at"]
    list_filter = ["kind", "urgency", "status", "created_at"]
    list_editable = ["status"]
    search_fields = ["name", "phone", "email", "site_name", "location", "lift_reference"]
    date_hierarchy = "created_at"
