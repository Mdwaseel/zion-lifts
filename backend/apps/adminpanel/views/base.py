"""The one viewset that serves every registered collection.

Everything that varies between collections — which columns, which filters, what
may be written — comes from the :class:`Resource` declaration, so this class is
written once and adding a model is a registry entry rather than a new module.

``for_resource`` builds a concrete subclass per resource at URL-configuration
time. DRF reads ``search_fields``/``filterset_fields``/``ordering_fields`` off
the class, so they have to be class attributes; closing over the resource in a
generated subclass gives DRF what it expects without any per-request work.
"""

from __future__ import annotations

from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .. import audit
from ..pagination import AdminPagination
from ..permissions import IsAdminPanelUser, ResourceAllowsMethod
from ..registry import Resource
from ..schema import describe_resource
from ..serializers import (
    BulkActionSerializer,
    ReferenceOptionSerializer,
    serializer_for,
)

# How many rows a relation picker offers before the client is expected to
# search. Large enough for every lookup table on this site, small enough that a
# picker on a big table cannot become an accidental full-table export.
OPTION_LIMIT = 200


class AdminResourceViewSet(viewsets.ModelViewSet):
    """CRUD for one registered resource. Subclassed per resource, never used raw."""

    resource: Resource
    permission_classes = [IsAdminPanelUser, ResourceAllowsMethod]
    pagination_class = AdminPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    def get_queryset(self):
        queryset = self.resource.model._default_manager.all()
        if self.resource.select_related:
            queryset = queryset.select_related(*self.resource.select_related)
        if self.resource.prefetch_related:
            queryset = queryset.prefetch_related(*self.resource.prefetch_related)
        return queryset.order_by(*self.resource.default_ordering)

    def get_serializer_class(self):
        return serializer_for(self.resource)

    # --- writes -----------------------------------------------------------
    # Each write records who did it. The message names the fields that changed
    # and never their values; see audit.describe_changes.
    def perform_create(self, serializer):
        instance = serializer.save()
        audit.record(self.request.user, instance, ADDITION, "Created from the control room.")

    def perform_update(self, serializer):
        changed = sorted(serializer.validated_data.keys())
        instance = serializer.save()
        audit.record(self.request.user, instance, CHANGE, audit.describe_changes(changed))

    def perform_destroy(self, instance):
        # Logged before the delete: afterwards the primary key is gone and the
        # entry would have nothing to point at.
        audit.record(self.request.user, instance, DELETION, "Deleted from the control room.")
        instance.delete()

    # --- extra routes -----------------------------------------------------
    @action(detail=False, methods=["get"])
    def schema(self, request):
        """Field-by-field description, so the form can render itself."""
        return Response(describe_resource(self.resource))

    @action(detail=False, methods=["get"])
    def options(self, request):
        """Choices for this resource's relation fields.

        Kept out of the schema because the schema is static and cacheable while
        these grow with the data. ``?field=`` narrows it to one relation, which
        is what a form needs; ``?q=`` searches within it.
        """
        wanted = request.query_params.get("field")
        query = (request.query_params.get("q") or "").strip()

        payload = {}
        for model_field in self.resource.model._meta.get_fields():
            if not isinstance(model_field, (models.ForeignKey, models.ManyToManyField)):
                continue
            if not getattr(model_field, "concrete", False):
                continue
            if wanted and model_field.name != wanted:
                continue
            payload[model_field.name] = ReferenceOptionSerializer(
                _option_queryset(model_field.related_model, query), many=True
            ).data
        return Response(payload)

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """Publish, unpublish or delete the checked rows.

        Doing this one request at a time is the difference between a usable
        table and a tedious one, and a single queryset write is also a single
        trip to the database.
        """
        form = BulkActionSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        verb = form.validated_data["action"]
        selected = self.get_queryset().filter(pk__in=form.validated_data["ids"])

        if verb == BulkActionSerializer.DELETE:
            if not self.resource.can_delete:
                return Response(
                    {"detail": "This collection cannot be deleted from."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Iterate rather than queryset.delete(): the audit trail should name
            # each record, and these collections are small enough that the extra
            # queries cost nothing a person would notice.
            affected = 0
            for instance in selected:
                audit.record(request.user, instance, DELETION, "Bulk delete.")
                instance.delete()
                affected += 1
            return Response({"detail": f"Deleted {affected} record(s).", "affected": affected})

        if not self.resource.can_edit:
            return Response(
                {"detail": "This collection is read-only."}, status=status.HTTP_403_FORBIDDEN
            )
        if not _has_field(self.resource.model, "is_published"):
            return Response(
                {"detail": "This collection has nothing to publish."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        publish = verb == BulkActionSerializer.PUBLISH
        instances = list(selected)
        affected = selected.update(is_published=publish)
        for instance in instances:
            audit.record(
                request.user, instance, CHANGE, f"Bulk {'publish' if publish else 'unpublish'}."
            )
        word = "Published" if publish else "Unpublished"
        return Response({"detail": f"{word} {affected} record(s).", "affected": affected})


class SingletonAdminViewSet(AdminResourceViewSet):
    """A collection with exactly one row, edited directly.

    Site settings is the only one. Showing a list of a single item and asking
    someone to click into it is a worse experience than opening the record, so
    the detail routes ignore the URL's id and always resolve to that one row.
    """

    def get_object(self):
        instance = self.get_queryset().first()
        if instance is None:
            # get_or_create rather than 404: the row is a configuration record
            # that is supposed to exist, and the panel should let it be filled
            # in rather than report that the site is broken.
            instance = self.resource.model._default_manager.create()
        self.check_object_permissions(self.request, instance)
        return instance


def _option_queryset(model: type[models.Model], query: str):
    queryset = model._default_manager.all()
    if query:
        # Every model in this project has a name or a title; fall back to the
        # primary key so an unusual one still filters rather than erroring.
        for candidate in ("name", "title", "question"):
            if _has_field(model, candidate):
                queryset = queryset.filter(**{f"{candidate}__icontains": query})
                break
    return queryset[:OPTION_LIMIT]


def _has_field(model: type[models.Model], name: str) -> bool:
    return any(f.name == name for f in model._meta.get_fields())


def for_resource(resource: Resource) -> type[AdminResourceViewSet]:
    """Build the concrete viewset class DRF will route to."""
    base = SingletonAdminViewSet if resource.singleton else AdminResourceViewSet
    return type(
        f"{resource.model.__name__}AdminViewSet",
        (base,),
        {
            "resource": resource,
            "queryset": resource.model._default_manager.all(),  # DRF basename introspection
            "search_fields": list(resource.search_fields),
            "filterset_fields": list(resource.filter_fields),
            "ordering_fields": list(resource.ordering_fields),
            "ordering": list(resource.default_ordering),
        },
    )
