"""Django authentication backend that accepts an email address.

The project uses the stock ``auth.User``, whose natural key is ``username``.
Rather than migrate to a custom user model — the database already has data and
five apps of migrations behind it — this backend resolves an email to that same
user and then defers entirely to ``ModelBackend`` for the password check,
``is_active`` handling and permissions.

Registering it also lets the Django admin's own login form take an email, so
the two front doors behave the same way.
"""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

log = logging.getLogger("apps.accounts.security")

UserModel = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """Look the user up by email first, then by username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(UserModel.USERNAME_FIELD) or kwargs.get("email")
        if not identifier or password is None:
            return None

        user = self._find(identifier)
        if user is None:
            # Run the hasher anyway. Returning early on an unknown address makes
            # the response measurably faster and turns login into an account
            # enumeration oracle.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _find(self, identifier: str):
        identifier = identifier.strip()
        matches = list(UserModel.objects.filter(email__iexact=identifier)[:2])

        if len(matches) > 1:
            # auth.User does not enforce a unique email, so this is possible.
            # Refusing is the only safe answer: we cannot know which account the
            # password was meant for.
            log.warning(
                "Login refused: %d accounts share an email address", len(matches)
            )
            return None
        if matches:
            return matches[0]

        return UserModel.objects.filter(**{UserModel.USERNAME_FIELD: identifier}).first()
