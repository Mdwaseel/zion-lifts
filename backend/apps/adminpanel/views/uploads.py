"""Where a picture or a film from someone's computer arrives.

One endpoint, deliberately generic: ``POST /api/admin/uploads/`` takes a file
and answers with the URL it was stored at. It is not tied to a model or a field,
because the panel already has one form component serving every collection — an
upload route per collection would be twenty-odd routes doing the same thing.

The field the URL ends up in is the form's business, not this endpoint's. That
separation is what lets a media field stay a plain ``CharField``: the record is
saved by the ordinary resource endpoint, carrying a string like any other.

Staff only, like everything else in this app. Uploading is a write, and an open
upload endpoint is a free file host.

**Not in the audit trail.** ``audit.record`` writes a ``LogEntry`` against a
model row, and an upload has no row — it is bytes on disk that nothing points at
until somebody saves a record referencing it. That save *is* audited, with the
field that changed, which is the answer to "who put this photograph on the lift
page". A log line here covers the gap in between.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import uploads
from ..permissions import IsAdminPanelUser

log = logging.getLogger("apps.adminpanel")


class UploadView(APIView):
    """``POST /api/admin/uploads/`` — store one file, return its URL."""

    permission_classes = [IsAdminPanelUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "No file was sent."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            stored = uploads.store(upload, folder=request.data.get("folder", "content"))
        except ValidationError as error:
            # These messages are written for the person at the keyboard — which
            # type, which limit — so they are safe and useful to show verbatim.
            return Response(
                {"detail": " ".join(error.messages)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            log.exception("admin upload failed | user=%s", request.user.pk)
            return Response(
                {"detail": "That file could not be stored. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        log.info(
            "admin upload stored | user=%s kind=%s size=%s url=%s",
            request.user.pk, stored.kind, stored.size, stored.url,
        )
        return Response(stored.as_dict(), status=status.HTTP_201_CREATED)
