"""Every collection the control room manages.

All of it comes from ``.models`` — this app's own — so the panel is no longer a
window onto five other apps' tables. Registration order is sidebar order and
``group`` is the sidebar heading, which makes this file the map of the panel:
read it top to bottom and you have read the navigation.

The consolidation shows up here as absences. There is no lift-images,
lift-variants or lift-specs collection, because those are lists inside the lift
form. There is no project-images and no project-categories, no journal-categories
and no faq-categories, and no legal-clauses. Editing a project is one screen.

A model absent from this file cannot be reached through the admin API at all.
"""

from apps.knowledge.models import Document, DocumentVersion, IngestionJob, KnowledgeBase

from .models import (
    FAQ,
    Application,
    Award,
    BlogPost,
    Certification,
    Component,
    Enquiry,
    Finish,
    GalleryItem,
    LegalPage,
    Lift,
    Milestone,
    Office,
    Partner,
    Project,
    SafetyFeature,
    ServicePillar,
    ServiceRequest,
    SiteSettings,
    Stat,
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
    key="faqs",
    model=FAQ,
    group=EDITORIAL,
    icon="help",
    list_display=("question", "category", "scope", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("question", "answer"),
    filter_fields=("category", "scope", "is_published"),
)

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
    key="milestones",
    model=Milestone,
    group=EDITORIAL,
    icon="calendar",
    list_display=("year", "title", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("title", "description"),
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

register(
    key="service-pillars",
    model=ServicePillar,
    group=EDITORIAL,
    icon="wrench",
    list_display=("name", "icon", "order", "is_published"),
    list_editable=("order", "is_published"),
    slug_source=("slug", "name"),
)

# One row per policy page, clauses included. The clause table is gone.
register(
    key="legal-pages",
    model=LegalPage,
    group=EDITORIAL,
    icon="document",
    label="Legal page",
    list_display=("title", "slug", "effective_date", "is_published"),
    list_editable=("is_published",),
    search_fields=("title", "intro"),
    slug_source=("slug", "title"),
    fieldsets=(
        ("Identity", ("title", "slug", "effective_date")),
        ("Copy", ("intro", "clauses")),
        PUBLISHING,
    ),
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
    key="stats",
    model=Stat,
    group=ORGANISATION,
    icon="gauge",
    list_display=("value", "label", "group", "order", "is_published"),
    list_editable=("order", "is_published"),
    filter_fields=("group", "is_published"),
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

register(
    key="certifications",
    model=Certification,
    group=ORGANISATION,
    icon="shield",
    list_display=("name", "issuer", "reference", "order", "is_published"),
    list_editable=("order", "is_published"),
    search_fields=("name", "issuer", "reference"),
)


# --- Knowledge base --------------------------------------------------------
# The assistant's corpus, and the one part of the panel that is not this app's
# own models. It stays in ``apps.knowledge`` because it is not content: a
# document crosses a service boundary to a worker and a vector index, and those
# records answer questions ("which edition is live?") that no amount of CRUD
# would. What the registry adds is the part that genuinely is CRUD — browsing,
# filtering by status, renaming. Uploading and deleting live at
# /api/admin/knowledge/, where they can queue a job and clear the index.
register(
    key="knowledge-bases",
    model=KnowledgeBase,
    group=KNOWLEDGE,
    icon="library",
    label="Knowledge base",
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

register(
    key="knowledge-documents",
    model=Document,
    group=KNOWLEDGE,
    icon="file-text",
    label="Document",
    can_create=False,
    can_delete=False,
    list_display=(
        "name", "knowledge_base", "status", "active_version", "file_size", "updated_at",
    ),
    search_fields=("name", "original_filename"),
    filter_fields=("knowledge_base", "status"),
    select_related=("knowledge_base", "active_version"),
    readonly_fields=(
        "original_filename", "mime_type", "file_size", "status",
        "active_version", "created_by",
    ),
    fieldsets=(
        ("Document", ("name", "knowledge_base")),
        ("File", ("original_filename", "mime_type", "file_size")),
        ("Processing", ("status", "active_version", "created_by")),
    ),
)

# A version is one immutable edition of a document's bytes. Nothing about it is
# editable by hand: changing any of these would describe an index that was
# built from something else.
register(
    key="knowledge-versions",
    model=DocumentVersion,
    group=KNOWLEDGE,
    icon="layers",
    label="Document version",
    can_create=False,
    can_edit=False,
    can_delete=False,
    parent_field="document",
    list_display=(
        "version_number", "document", "status", "page_count", "chunk_count",
        "embedding_model", "embedding_dimension", "created_at",
    ),
    filter_fields=("status", "document", "embedding_model"),
    search_fields=("content_hash",),
    select_related=("document",),
)

# The record of one attempt. Kept rather than overwritten: three failures and
# one failure are different problems.
register(
    key="knowledge-jobs",
    model=IngestionJob,
    group=KNOWLEDGE,
    icon="activity",
    label="Ingestion job",
    can_create=False,
    can_edit=False,
    can_delete=False,
    parent_field="document",
    list_display=(
        "job_type", "document", "status", "progress", "current_stage",
        "attempt_count", "error_code", "created_at", "started_at", "finished_at",
    ),
    filter_fields=("job_type", "status", "document"),
    search_fields=("celery_task_id", "error_code"),
    select_related=("document", "document_version"),
)
