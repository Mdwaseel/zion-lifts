"""The public tracking route, mounted at ``/api/analytics/``.

Kept apart from the admin routes in ``urls.py`` so the separation is structural
rather than a matter of remembering a permission class: this module is reachable
without a session, and everything in it is written to be.
"""

from django.urls import path

from . import public_views

app_name = "analytics-public"

urlpatterns = [
    path("track/", public_views.TrackView.as_view(), name="track"),
]
