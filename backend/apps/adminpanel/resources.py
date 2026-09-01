"""Every collection the control room manages.

All of it comes from ``.models`` — this app's own — so the panel is no longer a
window onto five other apps' tables. Registration order is sidebar order and
``group`` is the sidebar heading, which makes this file the map of the panel:
read it top to bottom and you have read the navigation.

The consolidation shows up here as absences. There is no lift-images,
lift-variants or lift-specs collection, because those are lists inside the lift
form. There is no project-images and no project-categories, and no
journal-categories. Editing a project is one screen.

Six collections are absent for a different reason: FAQs, milestones,
certifications, service pillars, stat rows and legal pages were content that
never changed between deploys, so they are static modules in
``frontend/src/data/`` and have no table, no endpoint and no screen. Giving an
operator a form for text nobody edits is not a feature.

A model absent from this file cannot be reached through the admin API at all.
"""

from apps.knowledge.models import KnowledgeBase

from .models import (
    Application,
    Award,
    BlogPost,
    Component,
    Enquiry,
    Finish,
    GalleryItem,
    Lift,
    Office,
    Partner,
    Project,
    SafetyFeature,
    ServiceRequest,
    SiteSettings,
    TeamMember,
    Testimonial,
)
from .registry import register

INBOX = "Inbox"
CATALOGUE = "Lifts"
PROJECTS = "Projects"
BLOGS = "Blogs"
EDITORIAL = "Editorial"
ORGANISATION = "Site settings"
KNOWLEDGE = "Knowledge base"

# Publishing controls repeat on nearly every content model.
PUBLISHING = ("Publishing", ("order", "is_published"))


# --- Inbox -----------------------------------------------------------------
# What staff open first, so it is registered first. Neither collection can be
# created or deleted here: these are records of something a customer sent, and
# the panel's job is to work them, not to author them.
register(
    key="enquiries",
    model=Enquiry,
    group=INBOX,
    icon="inbox",
    list_display=("name", "phone", "email", "property_type", "status", "created_at"),
    list_editable=("status",),
    search_fields=("name", "phone", "email", "organisation", "location", "message"),
    filter_fields=("status", "property_type", "project_stage", "installation_kind"),
    default_ordering=("-created_at",),
    select_related=("lift",),
    readonly_fields=(
        # Everything the customer typed. Staff annotate an enquiry; editing what
        # someone said they wanted would quietly destroy the record of it.
        "name", "phone", "email", "organisation", "message", "consent",
        "property_type", "project_stage", "location", "floors", "lift",
        "lift_type_note", "capacity", "stops", "installation_kind",
        "configuration", "attachments", "source_path", "created_at", "updated_at",
    ),
    fieldsets=(
        ("Handling", ("status", "internal_notes")),
        ("Contact", ("name", "phone", "email", "organisation")),
        ("Project", ("property_type", "project_stage", "location", "floors")),
        ("Configuration", ("lift", "lift_type_note", "capacity", "stops",
                           "installation_kind", "configuration")),
        ("Brief", ("message", "consent", "attachments", "source_path")),
    ),
    can_create=False,
    can_delete=False,
)

register(
    key="service-requests",
    model=ServiceRequest,
    group=INBOX,
    icon="wrench",
    list_display=("name", "kind", "urgency", "site_name", "phone", "status", "created_at"),
    list_editable=("status",),
    search_fields=("name", "phone", "email", "site_name", "location", "lift_reference"),
    filter_fields=("kind", "urgency", "status"),
    default_ordering=("-created_at",),
    readonly_fields=(
        "name", "phone", "email", "site_name", "location", "lift_reference",
        "message", "consent", "kind", "urgency", "created_at", "updated_at",
    ),
    fieldsets=(
        ("Handling", ("status", "internal_notes")),
        ("Request", ("kind", "urgency", "site_name", "location", "lift_reference")),
        ("Contact", ("name", "phone", "email")),
        ("Detail", ("message", "consent")),
    ),
    can_create=False,
    can_delete=False,
)


# --- Lifts -----------------------------------------------------------------
# One collection, not four. Images, variants and spec rows are lists on the
# lift, edited in the same form as the copy they belong to.
register(
    key="lifts",
    model=Lift,
    group=CATALOGUE,
    icon="lift",
    list_display=("name", "tagline", "capacity", "speed", "order", "is_featured", "is_published"),
    list_editable=("order", "is_featured", "is_published"),
    search_fields=("name", "tagline", "summary"),
    filter_fields=("is_featured", "is_published"),
    slug_source=("slug", "name"),
    prefetch_related=("applications", "safety_features"),
    fieldsets=(
        ("Identity", ("name", "slug", "short_name", "eyebrow", "tagline", "accent")),
        ("Copy", ("summary", "overview")),
        ("Headline specs", ("speed", "capacity", "stops", "drive")),
        ("Selector ranges", ("min_floors", "max_floors", "min_persons", "max_persons",
                             "pit_depth", "headroom", "shaft_footprint", "machine_room")),
        ("Media", ("hero_image_url", "hero_video_url", "images")),
        ("Variants and specs", ("variants", "specs")),
        ("Relations", ("applications", "safety_features")),
        ("Publishing", ("order", "is_featured", "is_published")),
    ),
)

register(
    key="finishes",
    model=Finish,
    group=CATALOGUE,
    icon="swatch",
    list_display=("name", "category", "swatch_hex", "tier", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "description"),
    filter_fields=("category", "tier", "is_published"),
)

register(
    key="applications",
    model=Application,
    group=CATALOGUE,
    icon="grid",
    list_display=("name", "group", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "description"),
    filter_fields=("group", "is_published"),
    slug_source=("slug", "name"),
)

register(
    key="safety-features",
    model=SafetyFeature,
    group=CATALOGUE,
    icon="shield",
    list_display=("name", "standard", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "headline", "description", "standard"),
    filter_fields=("is_published",),
    slug_source=("slug", "name"),
)

register(
    key="components",
    model=Component,
    group=CATALOGUE,
    icon="cog",
    list_display=("index", "name", "supplier", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "supplier"),
    filter_fields=("is_published",),
    slug_source=("slug", "name"),
)


# --- Projects --------------------------------------------------------------
# The whole case study — story, specification, and every photograph — on one
# screen. ``category`` is a choice and ``images`` is a list, so this is the only
# project collection there is.
register(
    key="projects",
    model=Project,
    group=PROJECTS,
    icon="building",
    list_display=("name", "location", "category", "lift", "year",
                  "is_featured", "order", "is_published"),
    list_editable=("order", "is_featured", "is_published"),
    search_fields=("name", "client", "location", "summary"),
    filter_fields=("category", "lift", "year", "is_featured", "is_published"),
    slug_source=("slug", "name"),
    select_related=("lift",),
    fieldsets=(
        ("Identity", ("name", "slug", "client", "location", "year", "category", "lift")),
        ("Story", ("statement", "summary", "challenge", "solution", "result")),
        ("Specification", ("system", "capacity", "stops", "door", "drive", "scope")),
        ("Media", ("hero_image_url", "hero_video_url", "loop_video_url",
                   "poster_url", "is_portrait")),
        ("Photographs", ("images",)),
        ("Publishing", ("order", "is_featured", "is_published")),
    ),
)


# --- Blogs -----------------------------------------------------------------
register(
    key="blogs",
    model=BlogPost,
    group=BLOGS,
    icon="article",
    label="Blog post",
    label_plural="Blogs",
    list_display=("title", "category", "published_at", "is_featured", "is_published"),
    list_editable=("is_featured", "is_published"),
    search_fields=("title", "excerpt", "body"),
    filter_fields=("category", "is_featured", "is_published"),
    default_ordering=("-published_at",),
    slug_source=("slug", "title"),
    fieldsets=(
        ("Identity", ("title", "slug", "category", "published_at", "read_minutes")),
        ("Copy", ("excerpt", "body")),
        ("Media", ("hero_image_url",)),
        ("Publishing", ("order", "is_featured", "is_published")),
    ),
)


# --- Editorial -------------------------------------------------------------
register(
    key="testimonials",
    model=Testimonial,
    group=EDITORIAL,
    icon="quote",
    list_display=("name", "organisation", "project", "is_featured", "order", "is_published"),
    list_editable=("is_featured", "order", "is_published"),
    search_fields=("name", "organisation", "quote"),
    filter_fields=("is_featured", "is_published"),
    select_related=("project",),
)

register(
    key="gallery",
    model=GalleryItem,
    group=EDITORIAL,
    icon="image",
    list_display=("__str__", "title", "category", "meta", "is_featured", "order", "is_published"),
    list_editable=("is_featured", "order", "is_published"),
    search_fields=("title", "meta"),
    filter_fields=("category", "is_featured", "is_published"),
)

register(
    key="team",
    model=TeamMember,
    group=EDITORIAL,
    icon="users",
    list_display=("name", "role", "department", "is_leadership", "order", "is_published"),
    list_editable=("is_leadership", "order", "is_published"),
    search_fields=("name", "role", "bio"),
    filter_fields=("department", "is_leadership", "is_published"),
)

register(
    key="awards",
    model=Award,
    group=EDITORIAL,
    icon="award",
    list_display=("name", "organisation", "year", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "organisation"),
)


# --- Site settings ---------------------------------------------------------
register(
    key="site-settings",
    model=SiteSettings,
    group=ORGANISATION,
    icon="settings",
    singleton=True,
    can_delete=False,
    fieldsets=(
        ("Identity", ("company_name", "tagline", "statement")),
        ("Contact", ("phone", "phone_service", "whatsapp", "email", "email_service")),
        ("Proof", ("founded_year", "installations", "team_size")),
        ("Location", ("city", "country")),
        ("Social", ("instagram", "linkedin", "youtube")),
    ),
)

register(
    key="offices",
    model=Office,
    group=ORGANISATION,
    icon="pin",
    list_display=("name", "kind", "city", "phone", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "address", "locality", "city"),
    filter_fields=("kind", "city", "is_published"),
    fieldsets=(
        ("Identity", ("name", "kind", "note")),
        ("Address", ("address", "locality", "city", "state", "postcode")),
        ("Contact", ("phone", "email", "hours")),
        ("Map", ("latitude", "longitude", "map_embed_url", "directions_url")),
        PUBLISHING,
    ),
)

register(
    key="partners",
    model=Partner,
    group=ORGANISATION,
    icon="handshake",
    list_display=("name", "role", "component", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "component"),
    filter_fields=("role", "is_published"),
)


# --- Knowledge base --------------------------------------------------------
# One entry, and it is here only to put "Knowledge base" in the sidebar and give
# the dashboard something to count. The screen behind it is not a generic list:
# adding data to the assistant's corpus means uploading a file and watching it
# be extracted, chunked, embedded and indexed, and none of that is a row write.
# That screen talks to /api/admin/knowledge/ instead — see apps/knowledge/api.
#
# Documents, versions and ingestion jobs used to be three more entries beside
# this one. They were three ways of looking at the same upload, and an operator
# whose job is "add this PDF" had to know which of the four to open. They are
# now sections of the one screen, reached by clicking the document they concern.
register(
    key="knowledge-bases",
    model=KnowledgeBase,
    group=KNOWLEDGE,
    icon="library",
    label="Knowledge base",
    # Singular in the sidebar: the heading above it already says "Knowledge
    # base", and "Knowledge base / Knowledge bases" reads like two things.
    label_plural="Knowledge base",
    list_display=("name", "slug", "is_active", "created_at"),
    list_editable=("is_active",),
    search_fields=("name", "slug", "description"),
    filter_fields=("is_active",),
    slug_source=("name", "slug"),
    fieldsets=(
        ("Identity", ("name", "slug", "description")),
        ("Availability", ("is_active",)),
    ),
)
