"""Checks that the seeded content is actually reachable through the public API.

The front end renders straight from these endpoints, so a shape change here is
a blank section on the site.
"""

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient


class SeededApiTests(TestCase):
    """Runs the real seeder, then asserts the API serves what the pages need."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def get(self, path, **params):
        res = self.client.get(path, params)
        self.assertEqual(res.status_code, 200, f"{path} -> {res.status_code}")
        return res.json()

    # --- collections the pages iterate over --------------------------------
    def test_every_collection_endpoint_returns_rows(self):
        expected = {
            "/api/lifts/": 9,
            "/api/projects/": 7,
            "/api/project-categories/": 6,
            "/api/applications/": 8,
            "/api/safety-features/": 7,
            "/api/finishes/": 23,
            "/api/components/": 8,
            # 32, not 37: five items captioned as Zion's own factory and
            # installation crews were licensed stock and have been removed.
            "/api/gallery/": 32,
            "/api/journal/": 6,
            "/api/faq-categories/": 6,
            "/api/testimonials/": 5,
            "/api/milestones/": 7,
            "/api/team/": 4,
            "/api/awards/": 3,
            "/api/service-pillars/": 5,
            "/api/partners/": 6,
            "/api/certifications/": 3,
        }
        for path, count in expected.items():
            with self.subTest(path=path):
                rows = self.get(path)
                rows = rows.get("results", rows) if isinstance(rows, dict) else rows
                self.assertEqual(len(rows), count)

    def test_site_settings_carries_the_offices(self):
        data = self.get("/api/site/")
        self.assertEqual(data["company_name"], "Zion Lifts")
        self.assertEqual(data["founded_year"], 2012)
        self.assertEqual(len(data["offices"]), 2)
        self.assertEqual(
            {o["kind"] for o in data["offices"]}, {"head_office", "factory"}
        )

    # --- detail payloads the product and case-study pages depend on --------
    def test_lift_detail_carries_everything_the_template_renders(self):
        lift = self.get("/api/lifts/home-elevator/")
        for key in ("overview", "images", "variants", "specs", "safety_features", "related"):
            self.assertIn(key, lift)
        self.assertTrue(lift["images"], "product page would have no gallery")
        self.assertTrue(lift["variants"])
        self.assertTrue(lift["specs"])
        self.assertTrue(lift["safety_features"])
        self.assertEqual(len(lift["related"]), 6)

    def test_project_detail_carries_the_case_study(self):
        project = self.get("/api/projects/lekha-nilayam/")
        for key in ("challenge", "solution", "result", "images", "related"):
            self.assertIn(key, project)
            self.assertTrue(project[key], f"{key} is empty")
        self.assertLessEqual(len(project["related"]), 3)

    def test_every_lift_and_project_has_a_hero_image(self):
        for lift in self.get("/api/lifts/"):
            with self.subTest(lift=lift["slug"]):
                self.assertTrue(lift["hero_image_url"])
        for project in self.get("/api/projects/"):
            with self.subTest(project=project["slug"]):
                self.assertTrue(project["hero_image_url"])

    def test_journal_body_is_only_on_the_detail_endpoint(self):
        listing = self.get("/api/journal/")
        self.assertNotIn("body", listing[0])
        detail = self.get(f"/api/journal/{listing[0]['slug']}/")
        self.assertTrue(detail["body"])

    def test_legal_documents_have_clauses(self):
        for slug, least in (("privacy", 8), ("terms", 10), ("cookies", 7)):
            with self.subTest(slug=slug):
                doc = self.get(f"/api/legal/{slug}/")
                self.assertGreaterEqual(len(doc["clauses"]), least)

    # --- filters the index pages use --------------------------------------
    def test_projects_filter_by_category_and_lift(self):
        residential = self.get("/api/projects/", **{"category__slug": "residential"})
        self.assertTrue(residential)
        self.assertTrue(all(p["category"]["slug"] == "residential" for p in residential))

        home = self.get("/api/projects/", **{"lift_type__slug": "home-elevator"})
        self.assertTrue(all(p["lift_type_slug"] == "home-elevator" for p in home))

    def test_faq_scope_filter_separates_contact_questions(self):
        contact = self.get("/api/faq-categories/", scope="contact")
        questions = [q for c in contact for q in c["questions"]]
        self.assertTrue(questions)
        self.assertTrue(all(q["scope"] == "contact" for q in questions))

    def test_finishes_group_into_the_configurator_categories(self):
        finishes = self.get("/api/finishes/")
        categories = {f["category"] for f in finishes}
        self.assertTrue({"material", "floor", "light", "door", "control"} <= categories)

    def test_unpublished_rows_are_hidden(self):
        from apps.catalog.models import LiftType

        lift = LiftType.objects.get(slug="dumbwaiter")
        lift.is_published = False
        lift.save()
        slugs = {l["slug"] for l in self.get("/api/lifts/")}
        self.assertNotIn("dumbwaiter", slugs)

    def test_seed_is_idempotent(self):
        from apps.catalog.models import LiftType
        from apps.projects.models import Project

        before = (LiftType.objects.count(), Project.objects.count())
        call_command("seed", verbosity=0)
        self.assertEqual((LiftType.objects.count(), Project.objects.count()), before)

    def test_a_missing_record_is_a_404_not_a_500(self):
        for path in ("/api/lifts/nope/", "/api/projects/nope/", "/api/journal/nope/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
