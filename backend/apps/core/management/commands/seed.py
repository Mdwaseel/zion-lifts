"""Populate the database with Zion's real catalogue, projects and editorial content.

Idempotent: every step uses update_or_create keyed on a natural key, so running
it again refreshes content without duplicating rows.

    python manage.py seed
    python manage.py seed --flush     # drop content first, then reseed
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.seed import catalog, content, projects, site


class Command(BaseCommand):
    help = "Seed the Zion Lifts site content."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing catalogue, project and editorial rows before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        steps = [
            ("Organisation", site.run),
            ("Catalogue", catalog.run),
            ("Projects", projects.run),
            ("Editorial", content.run),
        ]
        totals = {}
        for label, fn in steps:
            self.stdout.write(self.style.MIGRATE_HEADING(label))
            result = fn()
            totals.update(result)
            for key, value in result.items():
                self.stdout.write(f"  {key:<20} {value}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {sum(totals.values())} rows across {len(totals)} collections."
        ))

    def _flush(self):
        from apps.catalog.models import (
            Application, Component, FinishOption, LiftType, SafetyFeature,
        )
        from apps.content.models import (
            FAQ, Award, FAQCategory, GalleryItem, JournalCategory, JournalPost,
            LegalDocument, Milestone, ServicePillar, TeamMember, Testimonial,
        )
        from apps.core.models import Certification, Office, Partner, Stat
        from apps.projects.models import Project, ProjectCategory

        for model in (
            Testimonial, GalleryItem, JournalPost, JournalCategory, FAQ, FAQCategory,
            Milestone, TeamMember, Award, ServicePillar, LegalDocument,
            Project, ProjectCategory,
            LiftType, Application, SafetyFeature, FinishOption, Component,
            Office, Stat, Partner, Certification,
        ):
            count = model.objects.count()
            model.objects.all().delete()
            if count:
                self.stdout.write(f"  flushed {count:>4} {model.__name__}")
