"""Drop the six collections that became static content in the front end.

FAQs, milestones, certifications, service pillars, stat rows and the three legal
pages were each a table, a migration, a serializer, a public endpoint and an
admin form — rendering text that had not been edited since the seed wrote it.
Content that only changes when someone ships a deploy does not need a database
behind it, so it now lives in ``frontend/src/data/``, versioned alongside the
markup that renders it and present on the first paint rather than a round trip
later.

Nothing pointed at these tables. Every one was a leaf: no foreign key in this
app or any other referenced them, which is why they can go as a set without
ordering and why nothing else in the schema changes here.

Irreversible, deliberately. Django could recreate the six tables from the
historical models, but it cannot bring back the rows, and an empty ``faq`` table
that the site no longer reads is a worse state to roll back into than this one.
If the content is ever needed again it is in git — in ``frontend/src/data/`` on
this commit, and in ``apps/adminpanel/seed/`` on its parent.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0003_drop_legacy_tables"),
    ]

    operations = [
        migrations.DeleteModel(name="Certification"),
        migrations.DeleteModel(name="FAQ"),
        migrations.DeleteModel(name="LegalPage"),
        migrations.DeleteModel(name="Milestone"),
        migrations.DeleteModel(name="ServicePillar"),
        migrations.DeleteModel(name="Stat"),
    ]
