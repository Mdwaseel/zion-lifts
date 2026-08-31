"""Who is allowed into the control room."""

from __future__ import annotations

from rest_framework.permissions import BasePermission

ADMIN_DENIED = "This account does not have access to the control room."


def can_access_admin(user) -> bool:
    """The single answer to "may this account into the admin?".

    ``is_staff`` is the flag Django's own admin gates on, so using it here keeps
    one answer rather than two that can drift apart. Both the login view and the
    permission class below go through this function, so a future rule — an
    allow-list, a group, an MFA flag — is added in one place.
    """
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)


class IsStaffUser(BasePermission):
    """Authenticated *and* cleared for the admin.

    Use this on any endpoint that exposes administrative data. It is the DRF
    face of :func:`can_access_admin`.
    """

    message = ADMIN_DENIED

    def has_permission(self, request, view) -> bool:
        return can_access_admin(request.user)
