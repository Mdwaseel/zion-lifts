"""Populate the database with Zion's real catalogue, projects and editorial content.

Idempotent: every step uses ``update_or_create`` keyed on a natural key, so
running it again refreshes content without duplicating rows.

    python manage.py seed
    python manage.py seed --flush     # drop content first, then reseed
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.adminpanel.seed import catalog, content, projects, site


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
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {sum(totals.values())} rows across {len(totals)} collections."
            )
        )

    def _flush(self):
        """Clear the content tables. Enquiries are never touched.

        Order matters only where a foreign key does: testimonials and gallery
        items point at projects, and projects point at lifts. Everything else
        that used to need ordering — images, variants, specs, clauses — is a
        JSON column now and goes with its parent.
        """
        from apps.adminpanel.models import (
            FAQ,
            Application,
            Award,
            BlogPost,
            Certification,
            Component,
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
            Stat,
            TeamMember,
            Testimonial,
        )

        for model in (
            Testimonial, GalleryItem, Project, Lift, Application, SafetyFeature,
            Finish, Component, FAQ, BlogPost, Milestone, TeamMember, Award,
            ServicePillar, LegalPage, Office, Stat, Partner, Certification,
        ):
            model.objects.all().delete()
        self.stdout.write(self.style.WARNING("Flushed existing content."))
