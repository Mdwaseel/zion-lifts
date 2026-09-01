"""How much has come in that nobody has picked up yet.

The two inbox collections are the only things in the panel that arrive on their
own. Everything else changes because a member of staff changed it, so a badge on
it would only ever count their own work back at them. An enquiry, though, can sit
unopened over a weekend, and the sidebar is where somebody would notice.

**"Unread" is the record's own status, not a separate flag.** Both models already
have ``status="new"`` meaning "arrived, not yet picked up", and that is the
question a badge should answer. Adding an ``is_read`` column beside it would
create a second, quieter definition of the same thing — a record could then be
read but unhandled, or handled but unread, and the number on screen would stop
matching the filter it links to. The count clears when the status moves off
"new", which is the moment somebody actually did something about it.

Which collections have a badge, and what counts as unread, is declared on the
resource in ``resources.py`` — see ``Resource.unread_status``. Nothing here
knows what an enquiry is.
"""

from __future__ import annotations

from .registry import Resource, registry


def watched() -> list[Resource]:
    """The registered collections that declare an unread status."""
    return [resource for resource in registry if resource.unread_status]


def counts() -> dict[str, int]:
    """``{resource key: unread rows}``, one indexed COUNT each.

    Two queries today. Cheap enough to poll, and it stays cheap because the
    number of *watched* collections is what it scales with — not the number of
    records, and not the number of collections in the panel.
    """
    return {
        resource.key: resource.model._default_manager.filter(
            status=resource.unread_status
        ).count()
        for resource in watched()
    }


def summary() -> dict:
    """The payload both the sidebar and the poller read.

    One shape from one function so a badge and its total can never disagree —
    which they would within a request if each were computed where it was needed.
    """
    by_resource = counts()
    return {"counts": by_resource, "total": sum(by_resource.values())}
