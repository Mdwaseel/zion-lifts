from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Zion Lifts — Control Room"
admin.site.site_title = "Zion Lifts"
admin.site.index_title = "Site content"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.catalog.urls")),
    path("api/", include("apps.projects.urls")),
    path("api/", include("apps.content.urls")),
    path("api/", include("apps.enquiries.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
