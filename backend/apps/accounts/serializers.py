"""Request and response shapes for the authentication endpoints."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """Validates the *shape* of a login request only.

    Credentials and CAPTCHA are checked in the view, so that a wrong password
    and a wrong CAPTCHA can be answered with the deliberately vague messages the
    endpoint promises — a field-level error here would say which one was wrong.
    """

    email = serializers.EmailField(trim_whitespace=True)
    password = serializers.CharField(trim_whitespace=False, style={"input_type": "password"})
    captcha_id = serializers.CharField(max_length=64)
    captcha_answer = serializers.CharField(max_length=32, trim_whitespace=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class UserSerializer(serializers.ModelSerializer):
    """The public view of a user. Read-only, and holds nothing secret.

    Note what is absent: password, its hash, tokens, permissions payloads. The
    front end needs a name to greet and two flags to route on, and no more.
    """

    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "name", "is_staff", "is_superuser")
        read_only_fields = fields

    def get_name(self, user) -> str:
        return user.get_full_name() or user.get_username()
