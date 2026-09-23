"""Drop the five old apps' tables, once their content has been imported.

Django cannot do this for us. Deleting an app from ``INSTALLED_APPS`` takes its
models out of the graph but leaves the tables standing and its rows in
``django_migrations``, so the database keeps a second, stale copy of every
project, lift and enquiry — and ``showmigrations`` keeps listing apps that no
longer exist.

Ordering is left to ``CASCADE``: the legacy tables reference each other and
nothing outside this list, so dropping them as a set is safe, while dropping
them one at a time in the wrong order is not. ``IF EXISTS`` makes the whole
thing a no-op on a database that never had them.

Irreversible on purpose. Recreating empty legacy tables would restore the
schema and none of the data, which is worse than refusing.
"""

from django.db import migrations

LEGACY_TABLES = [
    # catalog
    "catalog_lifttype_applications",
    "catalog_lifttype_safety_features",
    "catalog_liftimage",
    "catalog_liftvariant",
    "catalog_liftspec",
    "catalog_lifttype",
    "catalog_application",
    "catalog_safetyfeature",
    "catalog_finishoption",
    "catalog_component",
    # projects
    "projects_projectimage",
    "projects_project",
    "projects_projectcategory",
    # content
    "content_faq",
    "content_faqcategory",
    "content_journalpost",
    "content_journalcategory",
    "content_testimonial",
    "content_galleryitem",
    "content_milestone",
    "content_teammember",
    "content_award",
    "content_servicepillar",
    "content_legalclause",
    "content_legaldocument",
    # core
    "core_sitesettings",
    "core_office",
    "core_stat",
    "core_partner",
    "core_certification",
    # enquiries
    "enquiries_enquiryattachment",
    "enquiries_enquiry",
    "enquiries_servicerequest",
]

LEGACY_APPS = ["catalog", "projects", "content", "core", "enquiries"]

DROP_TABLES = "\n".join(
    f'DROP TABLE IF EXISTS "{table}" CASCADE;' for table in LEGACY_TABLES
)

FORGET_MIGRATIONS = (
    "DELETE FROM django_migrations WHERE app IN ("
    + ", ".join(f"'{app}'" for app in LEGACY_APPS)
    + ");"
)


class Migration(migrations.Migration):

    dependencies = [("adminpanel", "0002_import_legacy_content")]

    operations = [
        migrations.RunSQL(DROP_TABLES, migrations.RunSQL.noop),
        migrations.RunSQL(FORGET_MIGRATIONS, migrations.RunSQL.noop),
    ]
