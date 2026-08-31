from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Zion Lifts — Control Room"
admin.site.site_title = "Zion Lifts"
admin.site.index_title = "Site content"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    # The custom control room's API. Django's own admin stays at /admin/.
    # Knowledge is mounted first: its routes are operations (upload, reindex)
    # that the registry's generic CRUD cannot express, and they must not be
    # shadowed by the catch-all resource router below.
    path("api/admin/knowledge/", include("apps.knowledge.api.urls")),
    # The ingestion worker's own routes. Not part of the staff API and not
    # reachable with a user credential — see apps/knowledge/api/internal.py.
    path("api/internal/knowledge/", include("apps.knowledge.api.internal_urls")),
    path("api/admin/", include("apps.adminpanel.urls")),
    # The website's own read-only API, over the same models.
    path("api/", include("apps.adminpanel.public.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
