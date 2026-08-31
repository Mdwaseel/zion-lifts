"""Routes for the ingestion worker, mounted at /api/internal/knowledge/.

A separate module from ``urls.py`` rather than a second list inside it. Both are
included by the project urlconf, and ``include()`` takes a module's whole
``urlpatterns`` — sharing one file would have mounted the staff-facing router
under the internal prefix, where its permission classes are the only thing that
would have stood between an unauthenticated caller and every document.
"""

from django.urls import path

from .internal import document_file, ingestion_report

app_name = "knowledge-internal"

urlpatterns = [
    path("ingestion-report/", ingestion_report, name="ingestion-report"),
    path("documents/file/", document_file, name="document-file"),
]
