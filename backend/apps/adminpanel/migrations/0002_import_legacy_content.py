"""Copy the site's content out of the five old apps and into this one.

The old shape had a table per child list and a table per category. This walks
each of those, collapses the children into JSON on their parent and the
categories into a slug on theirs, and writes the result here.

Primary keys are carried across deliberately. A project's id appears in the
control room's URLs, in Django's admin log, and in whatever anyone has
bookmarked; renumbering the rows would break all three for no gain. Postgres
sequences are reset at the end, because inserting explicit ids leaves them
pointing at 1 and the next create would collide.

Reversible in the only sense that matters here: reversing empties the new
tables and leaves the old ones untouched, which is what a rollback needs.

It declares no dependency on the five old apps, and cannot: they were removed
from ``INSTALLED_APPS`` once this had run, and a dependency on a migration
Django can no longer see fails the whole graph. Instead it asks for the old
models and returns quietly if they are not there — which is exactly the case on
a database that never had them, where there is nothing to import.
"""

from django.core.management.color import no_style
from django.db import migrations


def asset_url(instance, file_attr: str, url_attr: str) -> str:
    """The usable URL for an asset, uploaded or static.

    Same rule the old ``AssetField`` serialiser applied at render time. Applying
    it here means the JSON lists hold a URL the front end can use as-is,
    instead of a half-record the serialiser has to reassemble.
    """
    stored = getattr(instance, file_attr, None)
    if stored:
        try:
            return stored.url
        except ValueError:  # no file associated
            pass
    return getattr(instance, url_attr, "") or ""


def _attachment(attachment) -> dict:
    """One uploaded drawing, as a row in the enquiry's ``attachments`` list.

    ``size`` is read from storage and may not be there — a file deleted from
    disk should still leave a record of what was sent, not abort the migration.
    """
    stored = attachment.file
    try:
        size = stored.size
    except (OSError, ValueError):
        size = 0
    try:
        url = stored.url
    except ValueError:
        url = ""
    return {
        "name": attachment.original_name or stored.name,
        "path": stored.name,
        "url": url,
        "size": size,
        "uploaded_at": attachment.uploaded_at.isoformat(),
    }


def forwards(apps, schema_editor):
    try:
        _import_legacy(apps, schema_editor)
    except LookupError:
        # A fresh install: the old apps are gone, so there is no legacy content
        # and nothing for this migration to do.
        return


def _import_legacy(apps, schema_editor):
    # --- old -------------------------------------------------------------
    OldApplication = apps.get_model("catalog", "Application")
    OldSafetyFeature = apps.get_model("catalog", "SafetyFeature")
    OldFinish = apps.get_model("catalog", "FinishOption")
    OldComponent = apps.get_model("catalog", "Component")
    OldLift = apps.get_model("catalog", "LiftType")
    OldProject = apps.get_model("projects", "Project")
    OldJournalPost = apps.get_model("content", "JournalPost")
    OldFAQ = apps.get_model("content", "FAQ")
    OldTestimonial = apps.get_model("content", "Testimonial")
    OldGalleryItem = apps.get_model("content", "GalleryItem")
    OldMilestone = apps.get_model("content", "Milestone")
    OldTeamMember = apps.get_model("content", "TeamMember")
    OldAward = apps.get_model("content", "Award")
    OldServicePillar = apps.get_model("content", "ServicePillar")
    OldLegalDocument = apps.get_model("content", "LegalDocument")
    OldSiteSettings = apps.get_model("core", "SiteSettings")
    OldOffice = apps.get_model("core", "Office")
    OldStat = apps.get_model("core", "Stat")
    OldPartner = apps.get_model("core", "Partner")
    OldCertification = apps.get_model("core", "Certification")
    OldEnquiry = apps.get_model("enquiries", "Enquiry")
    OldServiceRequest = apps.get_model("enquiries", "ServiceRequest")

    # --- new -------------------------------------------------------------
    Application = apps.get_model("adminpanel", "Application")
    SafetyFeature = apps.get_model("adminpanel", "SafetyFeature")
    Finish = apps.get_model("adminpanel", "Finish")
    Component = apps.get_model("adminpanel", "Component")
    Lift = apps.get_model("adminpanel", "Lift")
    Project = apps.get_model("adminpanel", "Project")
    BlogPost = apps.get_model("adminpanel", "BlogPost")
    FAQ = apps.get_model("adminpanel", "FAQ")
    Testimonial = apps.get_model("adminpanel", "Testimonial")
    GalleryItem = apps.get_model("adminpanel", "GalleryItem")
    Milestone = apps.get_model("adminpanel", "Milestone")
    TeamMember = apps.get_model("adminpanel", "TeamMember")
    Award = apps.get_model("adminpanel", "Award")
    ServicePillar = apps.get_model("adminpanel", "ServicePillar")
    LegalPage = apps.get_model("adminpanel", "LegalPage")
    SiteSettings = apps.get_model("adminpanel", "SiteSettings")
    Office = apps.get_model("adminpanel", "Office")
    Stat = apps.get_model("adminpanel", "Stat")
    Partner = apps.get_model("adminpanel", "Partner")
    Certification = apps.get_model("adminpanel", "Certification")
    Enquiry = apps.get_model("adminpanel", "Enquiry")
    ServiceRequest = apps.get_model("adminpanel", "ServiceRequest")

    def copy(source_qs, Target, fields, **extra):
        """Straight field-for-field copy, ids included."""
        rows = [
            Target(
                pk=row.pk,
                **{name: getattr(row, name) for name in fields},
                **{name: fn(row) for name, fn in extra.items()},
            )
            for row in source_qs
        ]
        Target.objects.bulk_create(rows)
        return rows

    ORDERED = ["order", "is_published"]

    # --- catalogue lookups ------------------------------------------------
    copy(
        OldApplication.objects.all(),
        Application,
        ["slug", "name", "group", "description", "image_url", *ORDERED],
    )
    copy(
        OldSafetyFeature.objects.all(),
        SafetyFeature,
        ["slug", "name", "headline", "description", "test_procedure",
         "standard", "media_url", *ORDERED],
    )
    copy(
        OldFinish.objects.all(),
        Finish,
        ["category", "slug", "name", "description", "swatch_hex", "swatch_hex_2",
         "texture_url", "tier", *ORDERED],
        texture=lambda row: row.texture.name,
    )
    copy(
        OldComponent.objects.all(),
        Component,
        ["slug", "index", "name", "description", "detail", "supplier", *ORDERED],
    )

    # --- lifts: four tables become one row --------------------------------
    for old in OldLift.objects.prefetch_related("images", "variants", "specs"):
        lift = Lift.objects.create(
            pk=old.pk,
            slug=old.slug,
            name=old.name,
            short_name=old.short_name,
            eyebrow=old.eyebrow,
            tagline=old.tagline,
            summary=old.summary,
            overview=old.overview,
            speed=old.speed,
            capacity=old.capacity,
            stops=old.stops,
            drive=old.drive,
            min_floors=old.min_floors,
            max_floors=old.max_floors,
            min_persons=old.min_persons,
            max_persons=old.max_persons,
            pit_depth=old.pit_depth,
            headroom=old.headroom,
            shaft_footprint=old.shaft_footprint,
            machine_room=old.machine_room,
            hero_image_url=old.hero_image_url,
            hero_video_url=old.hero_video_url,
            accent=old.accent,
            is_featured=old.is_featured,
            order=old.order,
            is_published=old.is_published,
            images=[
                {
                    "kind": image.kind,
                    "src": asset_url(image, "image", "image_url"),
                    "alt": image.alt,
                    "caption": image.caption,
                }
                for image in old.images.order_by("order", "pk")
                if image.is_published
            ],
            variants=[
                {
                    "code": v.code,
                    "name": v.name,
                    "description": v.description,
                    "capacity": v.capacity,
                    "persons": v.persons,
                    "speed": v.speed,
                    "shaft": v.shaft,
                }
                for v in old.variants.order_by("order", "pk")
                if v.is_published
            ],
            specs=[
                {"group": s.group, "label": s.label, "value": s.value, "note": s.note}
                for s in old.specs.order_by("group", "order", "pk")
                if s.is_published
            ],
        )
        # The two genuine many-to-manys survive; ids match, so the through rows
        # can be written from the old ones directly.
        lift.applications.set(old.applications.values_list("pk", flat=True))
        lift.safety_features.set(old.safety_features.values_list("pk", flat=True))

    # --- projects: category becomes a slug, images become a list ----------
    for old in OldProject.objects.select_related("category", "lift_type").prefetch_related("images"):
        Project.objects.create(
            pk=old.pk,
            slug=old.slug,
            name=old.name,
            client=old.client,
            location=old.location,
            year=old.year,
            category=old.category.slug if old.category_id else "residential",
            lift_id=old.lift_type_id,
            statement=old.statement,
            summary=old.summary,
            challenge=old.challenge,
            solution=old.solution,
            result=old.result,
            system=old.system,
            capacity=old.capacity,
            stops=old.stops,
            door=old.door,
            drive=old.drive,
            scope=old.scope,
            hero_image_url=old.hero_image_url,
            hero_video_url=old.hero_video_url,
            loop_video_url=old.loop_video_url,
            poster_url=old.poster_url,
            is_portrait=old.is_portrait,
            is_featured=old.is_featured,
            order=old.order,
            is_published=old.is_published,
            images=[
                {
                    "stage": image.stage,
                    "src": asset_url(image, "image", "image_url"),
                    "caption": image.caption,
                    "alt": image.alt,
                }
                for image in old.images.order_by("order", "pk")
                if image.is_published
            ],
        )

    # --- editorial --------------------------------------------------------
    copy(
        OldJournalPost.objects.select_related("category"),
        BlogPost,
        ["slug", "title", "excerpt", "body", "hero_image_url", "read_minutes",
         "published_at", "is_featured", *ORDERED],
        category=lambda row: row.category.slug if row.category_id else "engineering",
    )
    copy(
        OldFAQ.objects.select_related("category"),
        FAQ,
        ["question", "answer", "link_label", "link_url", "scope", *ORDERED],
        category=lambda row: row.category.slug if row.category_id else "choosing-a-lift",
    )
    copy(
        OldTestimonial.objects.all(),
        Testimonial,
        ["name", "role", "organisation", "location", "quote", "video_url",
         "poster_url", "is_featured", *ORDERED],
        project_id=lambda row: row.project_id,
    )
    copy(
        OldGalleryItem.objects.all(),
        GalleryItem,
        ["category", "title", "meta", "image_url", "width", "height",
         "is_featured", *ORDERED],
        image=lambda row: row.image.name,
        project_id=lambda row: row.project_id,
    )
    copy(
        OldMilestone.objects.all(),
        Milestone,
        ["year", "title", "description", "image_url", *ORDERED],
    )
    copy(
        OldTeamMember.objects.all(),
        TeamMember,
        ["name", "role", "department", "bio", "photo_url",
         "is_leadership", *ORDERED],
        photo=lambda row: row.photo.name,
    )
    copy(
        OldAward.objects.all(),
        Award,
        ["name", "organisation", "year", "description", "image_url", *ORDERED],
    )
    copy(
        OldServicePillar.objects.all(),
        ServicePillar,
        ["slug", "name", "description", "detail", "icon", *ORDERED],
    )

    for old in OldLegalDocument.objects.prefetch_related("clauses"):
        LegalPage.objects.create(
            pk=old.pk,
            slug=old.slug,
            title=old.title,
            intro=old.intro,
            effective_date=old.effective_date,
            clauses=[
                {"heading": clause.heading, "body": clause.body}
                for clause in old.clauses.order_by("order", "pk")
                if clause.is_published
            ],
        )

    # --- organisation -----------------------------------------------------
    for old in OldSiteSettings.objects.all()[:1]:
        SiteSettings.objects.create(
            pk=1,
            **{
                name: getattr(old, name)
                for name in (
                    "company_name", "tagline", "statement", "phone", "phone_service",
                    "whatsapp", "email", "email_service", "founded_year", "installations",
                    "team_size", "city", "country", "instagram", "linkedin", "youtube",
                )
            },
        )

    copy(
        OldOffice.objects.all(),
        Office,
        ["kind", "name", "address", "locality", "city", "state", "postcode",
         "phone", "email", "hours", "note", "latitude", "longitude",
         "map_embed_url", "directions_url", *ORDERED],
    )
    copy(
        OldStat.objects.all(),
        Stat,
        ["group", "value", "label", "caption", "count_from", *ORDERED],
    )
    copy(
        OldPartner.objects.all(),
        Partner,
        ["name", "role", "component", "logo_url", "website", *ORDERED],
        logo=lambda row: row.logo.name,
    )
    copy(
        OldCertification.objects.all(),
        Certification,
        ["name", "issuer", "reference", "description",
         "certificate_url", *ORDERED],
        certificate=lambda row: row.certificate.name,
    )

    # --- inbox: attachments become a list ---------------------------------
    for old in OldEnquiry.objects.select_related("lift_type").prefetch_related("attachments"):
        Enquiry.objects.create(
            pk=old.pk,
            property_type=old.property_type,
            project_stage=old.project_stage,
            location=old.location,
            floors=old.floors,
            lift_id=old.lift_type_id,
            lift_type_note=old.lift_type_note,
            capacity=old.capacity,
            stops=old.stops,
            installation_kind=old.installation_kind,
            configuration=old.configuration,
            name=old.name,
            phone=old.phone,
            email=old.email,
            organisation=old.organisation,
            message=old.message,
            consent=old.consent,
            source_path=old.source_path,
            status=old.status,
            internal_notes=old.internal_notes,
            attachments=[
                _attachment(attachment) for attachment in old.attachments.order_by("pk")
            ],
        )

    copy(
        OldServiceRequest.objects.all(),
        ServiceRequest,
        ["kind", "urgency", "name", "phone", "email", "site_name", "location",
         "lift_reference", "message", "consent", "status"],
    )

    # ``auto_now_add`` and ``auto_now`` stamp every row with the moment this
    # migration ran, whatever was passed to the constructor. The real dates are
    # restored here with ``update()``, which does not go through ``pre_save``.
    for Old, New in (
        (OldLift, Lift), (OldProject, Project), (OldJournalPost, BlogPost),
        (OldLegalDocument, LegalPage), (OldOffice, Office),
        (OldSiteSettings, SiteSettings), (OldEnquiry, Enquiry),
        (OldServiceRequest, ServiceRequest),
    ):
        for row in Old.objects.values("pk", "created_at", "updated_at"):
            New.objects.filter(pk=row["pk"]).update(
                created_at=row["created_at"], updated_at=row["updated_at"]
            )

    _reset_sequences(apps, schema_editor)


def _reset_sequences(apps, schema_editor):
    """Point each table's id sequence past the ids just inserted.

    ``bulk_create`` with explicit primary keys never advances the sequence, so
    without this the first record created through the panel would ask for id 1
    and hit a row that already exists.
    """
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    app_config = apps.get_app_config("adminpanel")
    statements = connection.ops.sequence_reset_sql(
        no_style(), list(app_config.get_models())
    )
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def backwards(apps, schema_editor):
    """Empty the new tables. The old ones were never touched, so they stand."""
    for model_name in (
        "Enquiry", "ServiceRequest", "Testimonial", "GalleryItem", "Project",
        "Lift", "Application", "SafetyFeature", "Finish", "Component",
        "BlogPost", "FAQ", "Milestone", "TeamMember", "Award", "ServicePillar",
        "LegalPage", "Office", "Stat", "Partner", "Certification", "SiteSettings",
    ):
        apps.get_model("adminpanel", model_name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("adminpanel", "0001_initial")]

    operations = [migrations.RunPython(forwards, backwards)]
