"""Serializers built from the registry rather than written per model.

One ``ModelSerializer`` subclass is generated for each registered resource and
cached. Writes take the ordinary DRF shape — plain values, foreign keys as ids —
so nothing clever is needed on the way in. Reads add two underscore-prefixed
extras the table needs and the form ignores:

``_str``     the model's own ``__str__``, so a row can be titled without the
             front end having to know which field is the name.
``_labels``  human text for choice and foreign-key fields, so a table cell can
             show "Under construction" or "Home Elevator" instead of "construction"
             or "7" without a second request.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers

from .registry import Resource
from .schema import editable_fields

_cache: dict[str, type[serializers.ModelSerializer]] = {}


def serializer_for(resource: Resource) -> type[serializers.ModelSerializer]:
    """The serializer class for a resource, built once and reused."""
    if resource.key not in _cache:
        _cache[resource.key] = _build(resource)
    return _cache[resource.key]


def _build(resource: Resource) -> type[serializers.ModelSerializer]:
    fields = editable_fields(resource)
    names = [f.name for f in fields]
    readonly = [n for n in resource.readonly_fields if n in names]

    # Fields whose stored value is not what a person should read in a table.
    label_fields = tuple(
        f.name
        for f in fields
        if f.choices or isinstance(f, (models.ForeignKey, models.ManyToManyField))
    )

    meta = type(
        "Meta",
        (),
        {
            "model": resource.model,
            "fields": ["id", *names],
            "read_only_fields": ["id", *readonly],
        },
    )

    return type(
        f"{resource.model.__name__}AdminSerializer",
        (AdminSerializer,),
        {"Meta": meta, "label_fields": label_fields},
    )


class AdminSerializer(serializers.ModelSerializer):
    """Base for every generated serializer. Holds the read-side extras."""

    label_fields: tuple[str, ...] = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["_str"] = str(instance)
        data["_labels"] = {
            name: label
            for name in self.label_fields
            if (label := self._label(instance, name)) is not None
        }
        return data

    def _label(self, instance, name: str) -> str | None:
        # get_FOO_display exists for any field with choices and is the only
        # thing that knows the human wording.
        display = getattr(instance, f"get_{name}_display", None)
        if callable(display):
            return display()

        value = getattr(instance, name, None)
        if value is None:
            return None
        if hasattr(value, "all"):  # many-to-many
            return ", ".join(str(item) for item in value.all())
        return str(value)


class ReferenceOptionSerializer(serializers.Serializer):
    """One entry in a relation picker."""

    value = serializers.IntegerField(source="pk")
    label = serializers.SerializerMethodField()

    def get_label(self, instance) -> str:
        return str(instance)


class BulkActionSerializer(serializers.Serializer):
    """Input for the list view's checkbox actions."""

    PUBLISH = "publish"
    UNPUBLISH = "unpublish"
    DELETE = "delete"
    ACTIONS = [PUBLISH, UNPUBLISH, DELETE]

    action = serializers.ChoiceField(choices=ACTIONS)
    ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False, max_length=500
    )


class AdminUserSerializer(serializers.ModelSerializer):
    """Staff accounts, read-only. Managing users stays in Django's own admin."""

    name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ("id", "email", "name", "is_staff", "is_superuser", "last_login")
        read_only_fields = fields

    def get_name(self, user) -> str:
        return user.get_full_name() or user.get_username()


class AuditEntrySerializer(serializers.Serializer):
    """A row from Django's own admin log."""

    id = serializers.IntegerField()
    action = serializers.CharField()
    object_repr = serializers.CharField()
    object_id = serializers.CharField(allow_null=True)
    resource = serializers.CharField(allow_null=True)
    changes = serializers.CharField(allow_blank=True)
    user = serializers.CharField()
    at = serializers.DateTimeField()
