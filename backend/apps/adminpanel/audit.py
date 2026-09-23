"""Who changed what, recorded in Django's own admin log.

Deliberately not a new model. ``django.contrib.admin.models.LogEntry`` already
exists, is already migrated, and is already what /admin/ writes to — so reusing
it means a change made in the custom panel and the same change made in Django
admin land in one trail, in one order, readable from either. A second table
would have given the site two partial histories and no complete one.
"""

from __future__ import annotations

import logging

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import models

log = logging.getLogger("apps.adminpanel")

ACTION_NAMES = {ADDITION: "created", CHANGE: "updated", DELETION: "deleted"}


def record(user, instance: models.Model, action: int, message: str = "") -> None:
    """Write one entry. Never raises — an audit failure must not fail the edit.

    The alternative, letting a logging error roll back a save, would mean a
    broken log table stops the site being editable at all.
    """
    try:
        LogEntry.objects.log_action(
            user_id=user.pk,
            content_type_id=ContentType.objects.get_for_model(instance).pk,
            object_id=instance.pk,
            object_repr=str(instance)[:200],
            action_flag=action,
            change_message=message[:400],
        )
    except Exception:
        log.exception("Could not write an audit entry for %s", type(instance).__name__)


def describe_changes(fields: list[str]) -> str:
    """A short, human change message. Field names only — never their values.

    Values are not recorded on purpose: enquiries carry names, phone numbers and
    addresses, and an audit log that copies them turns one table of personal
    data into two.
    """
    if not fields:
        return "No fields changed."
    shown = ", ".join(sorted(fields)[:8])
    extra = len(fields) - 8
    return f"Changed {shown}" + (f" and {extra} more." if extra > 0 else ".")


def recent(limit: int = 12) -> list[dict]:
    """The latest entries, flattened for the dashboard."""
    from .registry import registry

    entries = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:limit]
    )

    rows = []
    for entry in entries:
        model = entry.content_type.model_class() if entry.content_type else None
        resource = registry.for_model(model) if model else None
        rows.append(
            {
                "id": entry.pk,
                "action": ACTION_NAMES.get(entry.action_flag, "changed"),
                "object_repr": entry.object_repr,
                # A deleted object has no page to link to.
                "object_id": entry.object_id if entry.action_flag != DELETION else None,
                "resource": resource.key if resource else None,
                "changes": entry.change_message or "",
                "user": entry.user.get_full_name() or entry.user.get_username(),
                "at": entry.action_time,
            }
        )
    return rows
