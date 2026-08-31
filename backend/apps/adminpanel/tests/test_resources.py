"""CRUD, search, filtering, bulk actions and the audit trail."""

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry

from apps.adminpanel.models import Application, Enquiry, Lift, Milestone, SiteSettings

from .base import API, AdminPanelTestCase


class ListTests(AdminPanelTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for n in range(30):
            Milestone.objects.create(
                year=f"20{n:02d}", title=f"Milestone {n}", order=n, is_published=n % 2 == 0
            )

    def test_a_list_is_paginated_with_the_counts_a_pager_needs(self):
        body = self.get("/milestones/")

        self.assertEqual(body["count"], 30)
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["pages"], 2)
        self.assertEqual(len(body["results"]), 25)

    def test_page_size_can_be_raised_but_not_without_limit(self):
        self.assertEqual(len(self.get("/milestones/", page_size=5)["results"]), 5)
        # max_page_size caps it; asking for everything must not be a way to
        # dump a table in one request.
        self.assertEqual(len(self.get("/milestones/", page_size=10_000)["results"]), 30)

    def test_rows_carry_a_display_string_for_the_table(self):
        row = self.get("/milestones/")["results"][0]
        self.assertIn("_str", row)
        self.assertTrue(row["_str"])

    def test_search_matches_the_declared_fields(self):
        body = self.get("/milestones/", search="Milestone 7")
        self.assertTrue(body["count"] >= 1)
        self.assertIn("Milestone 7", [r["title"] for r in body["results"]])

    def test_results_can_be_filtered(self):
        body = self.get("/milestones/", is_published="false")
        self.assertEqual(body["count"], 15)
        self.assertTrue(all(r["is_published"] is False for r in body["results"]))

    def test_is_published_is_filterable_without_being_declared(self):
        """The registry adds it wherever the model has it; see Resource.__post_init__."""
        from apps.adminpanel.registry import registry

        for key in ("milestones", "awards", "testimonials", "lifts"):
            with self.subTest(resource=key):
                self.assertIn("is_published", registry[key].filter_fields)

    def test_results_can_be_ordered(self):
        first = self.get("/milestones/", ordering="-order")["results"][0]
        self.assertEqual(first["order"], 29)

    def test_ordering_by_a_non_column_is_ignored_rather_than_a_500(self):
        # __str__ is a list column but not a database column; DRF drops any
        # ordering value not in ordering_fields.
        self.assertEqual(self.client.get(f"{API}/milestones/", {"ordering": "__str__"}).status_code, 200)


class WriteTests(AdminPanelTestCase):
    def test_a_record_can_be_created_and_is_logged(self):
        body = self.post("/milestones/", {"year": "2012", "title": "Founded"})

        self.assertEqual(body["title"], "Founded")
        entry = LogEntry.objects.latest("id")
        self.assertEqual(entry.action_flag, ADDITION)
        self.assertEqual(entry.user, self.staff)
        self.assertEqual(entry.object_repr, str(Milestone.objects.get(pk=body["id"])))

    def test_an_update_is_logged_with_the_field_names_that_changed(self):
        milestone = Milestone.objects.create(year="2012", title="Founded")
        self.patch(f"/milestones/{milestone.pk}/", {"title": "Founded in Hyderabad"})

        milestone.refresh_from_db()
        self.assertEqual(milestone.title, "Founded in Hyderabad")

        entry = LogEntry.objects.latest("id")
        self.assertEqual(entry.action_flag, CHANGE)
        self.assertIn("title", entry.change_message)

    def test_the_audit_message_names_fields_but_never_their_values(self):
        """An audit log that copies enquiry values becomes a second copy of it."""
        enquiry = Enquiry.objects.create(
            name="A Visitor", phone="9000000000", email="visitor@example.com"
        )
        self.patch(f"/enquiries/{enquiry.pk}/", {"internal_notes": "Called back on Tuesday"})

        entry = LogEntry.objects.latest("id")
        self.assertIn("internal_notes", entry.change_message)
        self.assertNotIn("Called back", entry.change_message)

    def test_a_delete_is_logged_before_the_row_disappears(self):
        milestone = Milestone.objects.create(year="2012", title="Founded")
        repr_before = str(milestone)

        res = self.client.delete(f"{API}/milestones/{milestone.pk}/")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Milestone.objects.filter(pk=milestone.pk).exists())

        entry = LogEntry.objects.latest("id")
        self.assertEqual(entry.action_flag, DELETION)
        self.assertEqual(entry.object_repr, repr_before)

    def test_readonly_fields_are_ignored_rather_than_written(self):
        enquiry = Enquiry.objects.create(name="A Visitor", phone="900", email="v@example.com")
        self.patch(f"/enquiries/{enquiry.pk}/", {"name": "Someone Else", "status": "contacted"})

        enquiry.refresh_from_db()
        self.assertEqual(enquiry.name, "A Visitor")  # what the customer sent, untouched
        self.assertEqual(enquiry.status, "contacted")  # what staff may change

    def test_validation_errors_come_back_per_field(self):
        res = self.client.post(f"{API}/milestones/", {"title": ""}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("title", res.json())

    def test_a_relation_is_written_by_id(self):
        lift = Lift.objects.create(slug="home", name="Home", tagline="t", summary="s")
        app = Application.objects.create(slug="villa", name="Villa")

        self.patch(f"/lifts/{lift.pk}/", {"applications": [app.pk]})
        self.assertEqual(list(lift.applications.values_list("pk", flat=True)), [app.pk])

    def test_labels_translate_ids_and_choices_for_the_table(self):
        lift = Lift.objects.create(slug="home", name="Home Elevator", tagline="t", summary="s")
        enquiry = Enquiry.objects.create(
            name="A Visitor", phone="900", email="v@example.com",
            property_type="villa", lift=lift,
        )
        row = self.get(f"/enquiries/{enquiry.pk}/")

        self.assertEqual(row["_labels"]["lift"], "Home Elevator")
        self.assertEqual(row["_labels"]["property_type"], "Villa / independent house")
        self.assertEqual(row["lift"], lift.pk)  # the id is still what writes


class BulkActionTests(AdminPanelTestCase):
    def setUp(self):
        super().setUp()
        self.rows = [
            Milestone.objects.create(year=f"200{n}", title=f"M{n}", is_published=False)
            for n in range(4)
        ]

    def ids(self, *indexes):
        return [self.rows[i].pk for i in indexes]

    def test_publishing_the_selected_rows(self):
        body = self.post(
            "/milestones/bulk/", {"action": "publish", "ids": self.ids(0, 1)}, expect=200
        )

        self.assertEqual(body["affected"], 2)
        self.assertTrue(Milestone.objects.get(pk=self.rows[0].pk).is_published)
        self.assertFalse(Milestone.objects.get(pk=self.rows[2].pk).is_published)

    def test_unpublishing_the_selected_rows(self):
        Milestone.objects.update(is_published=True)
        self.post("/milestones/bulk/", {"action": "unpublish", "ids": self.ids(0)}, expect=200)
        self.assertFalse(Milestone.objects.get(pk=self.rows[0].pk).is_published)

    def test_deleting_the_selected_rows_logs_each_one(self):
        before = LogEntry.objects.count()
        body = self.post(
            "/milestones/bulk/", {"action": "delete", "ids": self.ids(0, 1)}, expect=200
        )

        self.assertEqual(body["affected"], 2)
        self.assertEqual(Milestone.objects.count(), 2)
        self.assertEqual(LogEntry.objects.count(), before + 2)

    def test_bulk_delete_is_refused_on_a_collection_that_forbids_deletes(self):
        enquiry = Enquiry.objects.create(name="A Visitor", phone="900", email="v@example.com")
        res = self.client.post(
            f"{API}/enquiries/bulk/", {"action": "delete", "ids": [enquiry.pk]}, format="json"
        )
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Enquiry.objects.filter(pk=enquiry.pk).exists())

    def test_an_unknown_action_is_rejected(self):
        res = self.client.post(
            f"{API}/milestones/bulk/", {"action": "drop-table", "ids": self.ids(0)}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_an_empty_selection_is_rejected(self):
        res = self.client.post(
            f"{API}/milestones/bulk/", {"action": "publish", "ids": []}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_ids_outside_the_collection_are_simply_not_matched(self):
        body = self.post(
            "/milestones/bulk/", {"action": "publish", "ids": [999_999]}, expect=200
        )
        self.assertEqual(body["affected"], 0)


class SingletonTests(AdminPanelTestCase):
    def test_the_settings_row_is_created_on_first_read_rather_than_404ing(self):
        SiteSettings.objects.all().delete()

        body = self.get("/site-settings/1/")
        self.assertEqual(body["company_name"], "Zion Lifts")
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_any_id_resolves_to_the_one_row(self):
        settings_row = SiteSettings.objects.create()
        self.assertEqual(self.get("/site-settings/999/")["id"], settings_row.pk)

    def test_it_can_be_edited(self):
        SiteSettings.objects.create()
        self.patch("/site-settings/1/", {"tagline": "Precision in vertical movement."})
        self.assertEqual(SiteSettings.objects.get().tagline, "Precision in vertical movement.")


class OptionsTests(AdminPanelTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.lift = Lift.objects.create(slug="home", name="Home Elevator", tagline="t", summary="s")
        cls.app = Application.objects.create(slug="villa", name="Villa")

    def test_options_lists_the_relation_choices(self):
        body = self.get("/lifts/options/")

        self.assertIn("applications", body)
        self.assertEqual(body["applications"][0], {"value": self.app.pk, "label": "Villa"})

    def test_options_can_be_narrowed_to_one_field(self):
        body = self.get("/lifts/options/", field="applications")
        self.assertEqual(list(body), ["applications"])

    def test_options_can_be_searched(self):
        Application.objects.create(slug="hotel", name="Hotel")
        body = self.get("/lifts/options/", field="applications", q="vil")

        self.assertEqual([o["label"] for o in body["applications"]], ["Villa"])
