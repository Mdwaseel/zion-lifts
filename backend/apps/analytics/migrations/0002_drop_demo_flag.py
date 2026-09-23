"""Delete every seeded row, then remove the column that marked them.

The analytics tables shipped with an ``is_demo`` flag and a ``seed_analytics``
command, so a development database could be filled with plausible traffic
without that traffic reaching the dashboard's numbers in production. That is
gone: these tables now hold real visits and nothing else, the seeder has been
deleted, and there is no code path left that writes a synthetic row.

**Order matters here, and it is the whole point of this file.** ``is_demo`` is
the only thing that distinguishes a seeded row from a real one. Dropping the
column first would leave any demo rows already in the database permanently
indistinguishable from genuine traffic — silently inflating every number on the
dashboard forever, with no way to tell which rows to remove. So the purge runs
first, as a data migration, against the historical model that still has the
flag. Applying this migration to any database, in any state, therefore leaves
only real traffic behind.

The purge is deliberately irreversible. ``migrations.RunPython.noop`` is the
reverse, because un-applying this cannot invent the seeded rows back and should
not pretend otherwise — and nobody wants them back.

The indexes are rebuilt rather than merely renamed: they led with ``is_demo``
because that filter applied to every read, and with the filter gone the leading
column would be dead weight in front of the range scan that actually matters.
"""

from django.db import migrations, models


def purge_demo_rows(apps, schema_editor):
    """Remove every row the seeder created, in foreign-key order.

    Page views and sessions would cascade from their visitor, but they are
    deleted explicitly: a demo row whose visitor was somehow already gone would
    otherwise survive the cascade and outlive the column that identified it.
    """
    for model_name in ("PageView", "Session", "Visitor"):
        model = apps.get_model("analytics", model_name)
        model.objects.filter(is_demo=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        # First, while the flag still exists to identify them.
        migrations.RunPython(purge_demo_rows, migrations.RunPython.noop),

        migrations.RemoveIndex(model_name="pageview", name="an_pv_demo_created"),
        migrations.RemoveIndex(model_name="pageview", name="an_pv_demo_path_created"),
        migrations.RemoveIndex(model_name="session", name="an_sess_demo_started"),
        migrations.RemoveIndex(model_name="session", name="an_sess_demo_recent"),
        migrations.RemoveIndex(model_name="visitor", name="an_visitor_demo_first"),

        migrations.RemoveField(model_name="pageview", name="is_demo"),
        migrations.RemoveField(model_name="session", name="is_demo"),
        migrations.RemoveField(model_name="visitor", name="is_demo"),

        migrations.AddIndex(
            model_name="pageview",
            index=models.Index(fields=["created_at"], name="an_pv_created"),
        ),
        migrations.AddIndex(
            model_name="pageview",
            index=models.Index(fields=["path", "created_at"], name="an_pv_path_created"),
        ),
        migrations.AddIndex(
            model_name="session",
            index=models.Index(fields=["started_at"], name="an_sess_started"),
        ),
        migrations.AddIndex(
            model_name="session",
            index=models.Index(fields=["-last_activity_at"], name="an_sess_recent"),
        ),
        migrations.AddIndex(
            model_name="visitor",
            index=models.Index(fields=["first_seen"], name="an_visitor_first_seen"),
        ),
    ]
