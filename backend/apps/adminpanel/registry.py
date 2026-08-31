"""What the control room is allowed to manage, and how each collection behaves.

This is the one place a model becomes editable from the custom admin. Nothing
here queries or serialises anything — a :class:`Resource` is a declaration, and
``views/base.py`` is the single generic viewset that reads it. That is what
keeps twenty-four collections from becoming twenty-four viewsets.

Registering a model here exposes it at ``/api/admin/<key>/`` to staff users. A
model that is *not* registered is not reachable through this API at all, which
makes the registry the audit surface: to see what the panel can touch, read this
file and ``resources.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from django.db import models

# A form section: a title and the fields under it. Mirrors the shape Django's
# own ModelAdmin.fieldsets uses, so the two stay readable side by side.
Fieldset = tuple[str, tuple[str, ...]]


def sentence_case(text: str) -> str:
    """Capitalise the first letter and leave the rest alone.

    Not ``.title()``: that would turn the author's "FAQs" into "Faqs" and
    "FAQ categories" into "Faq Categories". Django's own default verbose names
    are already lowercase words, so lifting the first character is all they
    need, and a name someone wrote deliberately survives untouched.
    """
    text = str(text)
    return text[:1].upper() + text[1:] if text else text


@dataclass(frozen=True)
class Resource:
    """One editable collection.

    Only ``key``, ``model`` and ``group`` are required; everything else has a
    defensible default derived from the model, so registering a simple lookup
    table is a one-liner and only the collections that need care carry detail.
    """

    key: str
    model: type[models.Model]
    group: str

    # --- presentation -----------------------------------------------------
    label: str = ""
    label_plural: str = ""
    icon: str = "layers"
    # Columns in the list view, in order. Defaults to the model's __str__ alone.
    list_display: tuple[str, ...] = ()
    # Fields the list view may edit inline — publishing toggles and ordering,
    # which are tedious to change one record at a time.
    list_editable: tuple[str, ...] = ()

    # --- querying ---------------------------------------------------------
    search_fields: tuple[str, ...] = ()
    filter_fields: tuple[str, ...] = ()
    ordering_fields: tuple[str, ...] = ()
    default_ordering: tuple[str, ...] = ()

    # --- the form ---------------------------------------------------------
    # Sections for the edit form. Empty means "one section with every editable
    # field", which is right for small models and wrong for LiftType.
    fieldsets: tuple[Fieldset, ...] = ()
    readonly_fields: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    # Fill this slug from that field as the user types, the way Django's
    # prepopulated_fields does.
    slug_source: tuple[str, str] | None = None

    # --- behaviour --------------------------------------------------------
    can_create: bool = True
    can_edit: bool = True
    can_delete: bool = True
    # SiteSettings is a single row. The panel edits it directly rather than
    # showing a list of one.
    singleton: bool = False
    # The FK back to an owning resource, e.g. LiftImage.lift_type. The UI uses
    # it to offer "images for this lift" from the parent's page, and to filter.
    parent_field: str = ""
    # Relations worth pulling in one query for the list view.
    select_related: tuple[str, ...] = ()
    prefetch_related: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        meta = self.model._meta
        # dataclass is frozen, so defaults derived from the model have to go in
        # through object.__setattr__. Doing it here means every consumer sees a
        # fully populated Resource and none of them needs an "or fall back to"
        # branch of its own.
        if not self.label:
            object.__setattr__(self, "label", sentence_case(meta.verbose_name))
        if not self.label_plural:
            object.__setattr__(self, "label_plural", sentence_case(meta.verbose_name_plural))
        if not self.list_display:
            object.__setattr__(self, "list_display", ("__str__",))
        if not self.default_ordering:
            object.__setattr__(self, "default_ordering", tuple(meta.ordering) or ("-pk",))
        if not self.ordering_fields:
            object.__setattr__(self, "ordering_fields", self.concrete_sortable())

        # "Show me what isn't live yet" is the most useful filter in the panel
        # and the one the dashboard's unpublished counts link to. Nearly every
        # content model has the field, so it is added here rather than repeated
        # on twenty registrations and forgotten on the twenty-first.
        if self.has_field("is_published") and "is_published" not in self.filter_fields:
            object.__setattr__(self, "filter_fields", (*self.filter_fields, "is_published"))

    # --- derived ----------------------------------------------------------
    def has_field(self, name: str) -> bool:
        return any(f.name == name for f in self.model._meta.get_fields())

    def concrete_sortable(self) -> tuple[str, ...]:
        """List columns the database can actually sort on.

        ``__str__`` and any other computed column are dropped: asking the ORM to
        order by something that is not a column is a 500, and a column header
        that silently does nothing is worse than one that is not clickable.
        """
        names = {f.name for f in self.model._meta.get_fields() if getattr(f, "concrete", False)}
        return tuple(name for name in self.list_display if name in names)

    @property
    def app_label(self) -> str:
        return self.model._meta.app_label

    @property
    def model_name(self) -> str:
        return self.model._meta.model_name


class AlreadyRegistered(Exception):
    pass


class NotRegistered(KeyError):
    pass


class AdminRegistry:
    """The collection of registered resources, keyed by URL segment."""

    def __init__(self) -> None:
        self._resources: dict[str, Resource] = {}

    def register(self, resource: Resource) -> Resource:
        if resource.key in self._resources:
            raise AlreadyRegistered(f"{resource.key!r} is already registered")
        self._resources[resource.key] = resource
        return resource

    def __getitem__(self, key: str) -> Resource:
        try:
            return self._resources[key]
        except KeyError:
            raise NotRegistered(f"No admin resource named {key!r}") from None

    def get(self, key: str) -> Resource | None:
        return self._resources.get(key)

    def __iter__(self) -> Iterator[Resource]:
        return iter(self._resources.values())

    def __len__(self) -> int:
        return len(self._resources)

    def __contains__(self, key: object) -> bool:
        return key in self._resources

    def for_model(self, model: type[models.Model]) -> Resource | None:
        """The resource backing a model, used to turn a FK into a link."""
        return next((r for r in self if r.model is model), None)

    def grouped(self) -> list[dict]:
        """Resources bucketed by ``group``, in registration order.

        This is what the sidebar renders, so the order resources are registered
        in ``resources.py`` is the order they appear on screen.
        """
        groups: dict[str, list[Resource]] = {}
        for resource in self:
            groups.setdefault(resource.group, []).append(resource)
        return [{"group": name, "resources": items} for name, items in groups.items()]


registry = AdminRegistry()


def register(**kwargs) -> Resource:
    """Shorthand used throughout ``resources.py``."""
    return registry.register(Resource(**kwargs))
