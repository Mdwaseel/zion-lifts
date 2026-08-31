"""Who may use the control room, and what they may do in it.

Access is the same question the Django admin asks — ``is_staff`` — answered by
``apps.accounts.permissions.can_access_admin`` so there is one gate, not two.
This module adds the second question the panel needs: whether *this* resource
allows *this* verb, which the registry declares.
"""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.permissions import ADMIN_DENIED, can_access_admin


class IsAdminPanelUser(BasePermission):
    """Staff only. The gate on every endpoint in this app."""

    message = ADMIN_DENIED

    def has_permission(self, request, view) -> bool:
        return can_access_admin(request.user)


class ResourceAllowsMethod(BasePermission):
    """Enforces the registry's ``can_create`` / ``can_edit`` / ``can_delete``.

    Those flags exist so a collection can be exposed without being fully
    writable — site settings is a single row that must not be deleted, and an
    enquiry is a record of something a customer sent, which staff annotate
    rather than create. Checking them here means the rule is enforced by the
    permission layer for every action, rather than remembered in each handler.
    """

    message = "That action is not allowed on this collection."

    _VERB = {"POST": "can_create", "PUT": "can_edit", "PATCH": "can_edit", "DELETE": "can_delete"}

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True

        resource = getattr(view, "resource", None)
        if resource is None:
            return True

        # Bulk delete arrives as a POST, so the flag it needs is the one the
        # body asks for, not the one the method implies.
        if getattr(view, "action", None) == "bulk":
            return resource.can_edit or resource.can_delete

        flag = self._VERB.get(request.method)
        if flag == "can_create" and resource.singleton:
            return False
        return bool(flag is None or getattr(resource, flag))
