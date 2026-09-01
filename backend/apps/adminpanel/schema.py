"""Describes a model to the front end, field by field.

The React panel has one table component and one form component for all
twenty-four collections. It can only manage that if the server tells it what a
collection looks like — which fields exist, what type each is, which are
required, what a choice field's options are. That description is built here, by
reading Django's own model metadata, so it can never drift from the database:
add a field to a model and it appears in the form.

The contract is deliberately small. Every field is one of the ``FieldType``
values below, and the front end has one input per type.
"""

from __future__ import annotations

from typing import Any

from django.db import models

from .registry import Resource, registry, sentence_case

# Types the front end knows how to render. Anything unrecognised degrades to
# "string", which is editable and honest rather than hidden.
STRING = "string"
TEXT = "text"
SLUG = "slug"
EMAIL = "email"
URL = "url"
INTEGER = "integer"
FLOAT = "float"
BOOLEAN = "boolean"
DATE = "date"
DATETIME = "datetime"
CHOICE = "choice"
REFERENCE = "reference"
MULTI_REFERENCE = "multi_reference"
IMAGE = "image"
FILE = "file"
JSON = "json"
COLOR = "color"
# A URL string that names a picture or a film. Stored as a CharField, but there
# is no reason a person should ever type one: the panel renders an uploader,
# stores the file, and puts the resulting URL in the field. See uploads.py.
MEDIA = "media"
# A JSON list of media objects — a lift's images, a project's photographs. Same
# uploader, once per row, with the row's own text fields beside it.
MEDIA_LIST = "media_list"

_BY_FIELD_CLASS: list[tuple[type[models.Field], str]] = [
    # Order matters: the first match wins, so subclasses come before their
    # bases (SlugField before CharField, EmailField before CharField).
    (models.SlugField, SLUG),
    (models.EmailField, EMAIL),
    (models.URLField, URL),
    (models.ImageField, IMAGE),
    (models.FileField, FILE),
    (models.BooleanField, BOOLEAN),
    (models.DateTimeField, DATETIME),
    (models.DateField, DATE),
    (models.FloatField, FLOAT),
    (models.IntegerField, INTEGER),
    (models.JSONField, JSON),
    (models.TextField, TEXT),
    (models.CharField, STRING),
]

# Never editable, and never worth a form row.
ALWAYS_READONLY = frozenset({"id", "pk", "created_at", "updated_at"})

# --- media -----------------------------------------------------------------
# Which CharFields hold a media URL rather than a link somebody should type.
#
# Matched by name, because that is the only thing distinguishing them: they are
# all `CharField(max_length=300)`. The alternative — a flag on every one of the
# fourteen — would be a second thing to keep in step with the first, and the
# naming here is already consistent and load-bearing (the public serializers
# pair `logo`/`logo_url`, `image`/`image_url` on exactly this convention).
#
# `URLField` is deliberately excluded below: a map embed and a partner's website
# are genuinely somebody else's address, and an uploader would be nonsense there.
_IMAGE_FIELD_NAMES = frozenset(
    {"image_url", "hero_image_url", "photo_url", "logo_url", "poster_url", "texture_url"}
)
_VIDEO_FIELD_NAMES = frozenset(
    {"video_url", "hero_video_url", "loop_video_url", "media_url"}
)

# JSON list fields whose rows carry a `src`, and the shape of one row.
#
# Keyed by model, not by field name, because the two `images` columns are not
# the same shape: a lift's photographs are tagged `kind` (where on the product
# page they belong) and a project's are tagged `stage` (how far through the
# installation they were taken). Keying on "images" alone would put an
# irrelevant dropdown on every row of both.
#
# The item schema is what lets the panel draw a real form per photograph instead
# of handing an operator a textarea full of braces. The choices are the values
# actually present in the catalogue — a free-text box here is how a typo becomes
# a photograph that never appears on the site.
_ALT = {
    "name": "alt", "label": "Alt text", "type": STRING,
    "help_text": "What the photograph shows, for anyone who cannot see it.",
}
_CAPTION = {"name": "caption", "label": "Caption", "type": STRING}


def _choice(name, label, values):
    return {
        "name": name,
        "label": label,
        "type": CHOICE,
        "choices": [{"value": v, "label": t} for v, t in values],
    }


_MEDIA_LISTS: dict[str, dict] = {
    "adminpanel.lift.images": {
        "src_key": "src",
        "fields": [
            _choice("kind", "Shown as", [
                ("gallery", "Gallery"),
                ("detail", "Detail"),
                ("cabin", "Cabin"),
            ]),
            _ALT,
            _CAPTION,
        ],
    },
    "adminpanel.project.images": {
        "src_key": "src",
        "fields": [
            _choice("stage", "Stage", [
                ("site", "Site"),
                ("installation", "Installation"),
                ("interior", "Interior"),
                ("detail", "Detail"),
                ("completion", "Completion"),
            ]),
            _ALT,
            _CAPTION,
        ],
    },
}


def _media_list_key(model_field: models.Field) -> str:
    return f"{model_field.model._meta.label_lower}.{model_field.name}"


def _media_kind(model_field: models.Field) -> str | None:
    """"image", "video", or None if this field is not media."""
    if not isinstance(model_field, models.CharField) or isinstance(model_field, models.URLField):
        return None
    if model_field.name in _IMAGE_FIELD_NAMES:
        return "image"
    if model_field.name in _VIDEO_FIELD_NAMES:
        return "video"
    return None


def field_type(model_field: models.Field) -> str:
    """The front-end input a model field should be edited with."""
    if model_field.choices:
        return CHOICE
    if isinstance(model_field, models.ManyToManyField):
        return MULTI_REFERENCE
    if isinstance(model_field, models.ForeignKey):
        return REFERENCE

    # A hex colour is a CharField like any other; the only thing that marks it
    # out is the name. Worth the special case — a colour picker beats typing
    # "#C9B79A" by hand, and these drive the finish swatches on the site.
    if isinstance(model_field, models.CharField) and _looks_like_colour(model_field):
        return COLOR

    if _media_kind(model_field):
        return MEDIA

    if isinstance(model_field, models.JSONField) and _media_list_key(model_field) in _MEDIA_LISTS:
        return MEDIA_LIST

    for klass, name in _BY_FIELD_CLASS:
        if isinstance(model_field, klass):
            return name
    return STRING


def _is_required(model_field: models.Field, readonly: bool) -> bool:
    """Whether the API will refuse the record without a value.

    Mirrors DRF's own rule from ``rest_framework.utils.field_mapping``
    (``has_default() or blank or null`` makes a field optional), because the
    serializer built from this same model is what will actually enforce it. If
    this drifts, the form stars fields the server is happy to receive without —
    or worse, fails to star one it needs. ``test_schema_required_matches_the_
    serializer_for_every_resource`` holds the two together.
    """
    if readonly or not model_field.editable:
        return False
    return not (model_field.has_default() or model_field.blank or model_field.null)


def _looks_like_colour(model_field: models.CharField) -> bool:
    name = model_field.name
    return (model_field.max_length or 0) <= 9 and (
        name.endswith("_hex") or name in {"accent", "colour", "color"}
    )


def describe_field(model_field: models.Field, resource: Resource) -> dict[str, Any]:
    """One field, as the form renderer needs it."""
    kind = field_type(model_field)
    readonly = model_field.name in resource.readonly_fields or model_field.name in ALWAYS_READONLY

    described: dict[str, Any] = {
        "name": model_field.name,
        "label": _label_for(model_field),
        "type": kind,
        "required": _is_required(model_field, readonly),
        "readonly": readonly,
        "help_text": str(model_field.help_text or ""),
    }

    max_length = getattr(model_field, "max_length", None)
    if max_length and kind in {STRING, SLUG, EMAIL, URL, COLOR}:
        described["max_length"] = max_length

    if kind == MEDIA:
        described["media_kind"] = _media_kind(model_field)
        # Uploads are filed per collection, so the uploads directory stays
        # browsable by a human rather than becoming one flat folder of uuids.
        described["upload_folder"] = resource.key

    if kind == MEDIA_LIST:
        described.update(_MEDIA_LISTS[_media_list_key(model_field)])
        described["upload_folder"] = resource.key

    if kind == CHOICE:
        described["choices"] = [
            {"value": value, "label": str(label)} for value, label in model_field.choices
        ]

    if kind in {REFERENCE, MULTI_REFERENCE}:
        related_model = model_field.related_model
        related = registry.for_model(related_model)
        # Options are fetched separately: inlining every lift type into every
        # schema response would make the payload grow with the database.
        described["related_resource"] = related.key if related else None
        described["related_label"] = sentence_case(related_model._meta.verbose_name)

    if kind == SLUG and resource.slug_source and resource.slug_source[0] == model_field.name:
        described["slug_source"] = resource.slug_source[1]

    return described


def _label_for(model_field: models.Field) -> str:
    """Django's verbose_name in sentence case.

    Sentence case rather than title case so an author-written name keeps its own
    capitalisation — title case would render "FAQ" as "Faq" — and so the labels
    match the sidebar, which is built the same way.
    """
    return sentence_case(str(model_field.verbose_name))


def editable_fields(resource: Resource) -> list[models.Field]:
    """Concrete model fields the panel may write, in model declaration order."""
    fields = []
    for model_field in resource.model._meta.get_fields():
        if not getattr(model_field, "concrete", False) and not isinstance(
            model_field, models.ManyToManyField
        ):
            continue  # reverse relations are their own resource, not a form input
        if model_field.name in resource.exclude:
            continue
        if model_field.auto_created and not model_field.concrete:
            continue
        if isinstance(model_field, models.AutoField):
            continue
        fields.append(model_field)
    return fields


def describe_resource(resource: Resource, *, detail: bool = True) -> dict[str, Any]:
    """A resource as the sidebar, table and form all need it.

    ``detail=False`` trims the field list — the sidebar only needs names and
    permissions, and sending every field of every collection on first paint
    would be most of a megabyte for nothing.
    """
    described: dict[str, Any] = {
        "key": resource.key,
        "group": resource.group,
        "label": resource.label,
        "label_plural": resource.label_plural,
        "icon": resource.icon,
        "singleton": resource.singleton,
        "permissions": {
            "create": resource.can_create and not resource.singleton,
            "edit": resource.can_edit,
            "delete": resource.can_delete and not resource.singleton,
        },
        # The other collections reached from the same screen, owner first.
        # Empty for a resource that stands alone, which is how the list view
        # knows to render no tab bar rather than a bar with one tab in it.
        #
        # Carried on the resource's own description rather than looked up from
        # the navigation payload so the list screen stays self-contained: it
        # already fetches its schema, and this saves threading the sidebar's
        # data down through every route that might need it.
        "tabs": [
            {"key": member.key, "label": member.label_plural}
            for member in registry.section_members(resource.key)
        ],
    }
    if not detail:
        return described

    fields = [describe_field(f, resource) for f in editable_fields(resource)]
    by_name = {f["name"]: f for f in fields}

    described |= {
        "fields": fields,
        "list_display": list(resource.list_display),
        "list_editable": list(resource.list_editable),
        "search_fields": list(resource.search_fields),
        "ordering_fields": list(resource.ordering_fields),
        "default_ordering": list(resource.default_ordering),
        "parent_field": resource.parent_field,
        "filters": [by_name[name] for name in resource.filter_fields if name in by_name],
        "fieldsets": _fieldsets(resource, fields),
    }
    return described


def _fieldsets(resource: Resource, fields: list[dict]) -> list[dict]:
    """Form sections.

    A declared fieldset is honoured exactly, read-only fields included: an
    enquiry is almost entirely read-only, and a form that showed only the two
    fields staff may change would hide the enquiry itself. The front end renders
    those as text rather than inputs.

    With nothing declared the fallback is one unnamed section of the writable
    fields, so a small lookup table does not sprout "Created At" and "Updated
    At" rows nobody asked for.
    """
    known = {f["name"] for f in fields}
    writable = [f["name"] for f in fields if not f["readonly"]]

    if not resource.fieldsets:
        return [{"title": "", "fields": writable}]

    declared = {name for _, names in resource.fieldsets for name in names}
    sections = [
        {"title": title, "fields": [n for n in names if n in known]}
        for title, names in resource.fieldsets
    ]
    # A field added to the model but never added to a fieldset would otherwise
    # be invisible and un-editable — surface it rather than silently lose it.
    missing = [name for name in writable if name not in declared]
    if missing:
        sections.append({"title": "Other", "fields": missing})
    return [section for section in sections if section["fields"]]
