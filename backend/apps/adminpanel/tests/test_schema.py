"""The description the front end renders itself from.

One React table and one React form serve every collection, so a wrong schema is
a broken screen rather than a wrong value. These tests pin the contract.
"""

from apps.adminpanel import schema
from apps.adminpanel.registry import registry

from .base import AdminPanelTestCase

FIELD_KEYS = {"name", "label", "type", "required", "readonly", "help_text"}


class SchemaContractTests(AdminPanelTestCase):
    def test_every_resource_describes_itself_without_error(self):
        """A model registered with a bad declaration must fail here, not on screen."""
        for resource in registry:
            with self.subTest(resource=resource.key):
                described = schema.describe_resource(resource)
                self.assertTrue(described["fields"], f"{resource.key} described no fields")
                for field in described["fields"]:
                    self.assertTrue(FIELD_KEYS <= set(field), field)

    def test_every_field_type_is_one_the_front_end_knows(self):
        known = {
            schema.STRING, schema.TEXT, schema.SLUG, schema.EMAIL, schema.URL,
            schema.INTEGER, schema.FLOAT, schema.BOOLEAN, schema.DATE, schema.DATETIME,
            schema.CHOICE, schema.REFERENCE, schema.MULTI_REFERENCE, schema.IMAGE,
            schema.FILE, schema.JSON, schema.COLOR,
        }
        for resource in registry:
            for field in schema.describe_resource(resource)["fields"]:
                with self.subTest(resource=resource.key, field=field["name"]):
                    self.assertIn(field["type"], known)

    def test_list_and_filter_columns_all_exist_on_the_model(self):
        """Guards against a typo in resources.py becoming a 500 on a real table."""
        for resource in registry:
            names = {f["name"] for f in schema.describe_resource(resource)["fields"]}
            for column in resource.list_display:
                if column == "__str__":
                    continue
                with self.subTest(resource=resource.key, column=column):
                    self.assertIn(column, names)
            for column in (*resource.filter_fields, *resource.search_fields):
                with self.subTest(resource=resource.key, filter=column):
                    # Search fields may traverse relations with __; only the
                    # first segment has to be a field on this model.
                    self.assertIn(column.split("__")[0], names)

    def test_fieldsets_only_name_fields_that_exist(self):
        for resource in registry:
            names = {f["name"] for f in schema.describe_resource(resource)["fields"]}
            for title, fields in resource.fieldsets:
                for field in fields:
                    with self.subTest(resource=resource.key, section=title, field=field):
                        self.assertIn(field, names)

    def test_every_writable_field_appears_in_some_section(self):
        """A field nobody can reach is a field nobody can fill in."""
        for resource in registry:
            described = schema.describe_resource(resource)
            placed = {name for s in described["fieldsets"] for name in s["fields"]}
            writable = {f["name"] for f in described["fields"] if not f["readonly"]}
            with self.subTest(resource=resource.key):
                self.assertEqual(writable - placed, set())


class FieldTypeTests(AdminPanelTestCase):
    def field(self, resource_key: str, name: str) -> dict:
        described = schema.describe_resource(registry[resource_key])
        return next(f for f in described["fields"] if f["name"] == name)

    def test_a_choice_field_carries_its_options(self):
        field = self.field("enquiries", "status")

        self.assertEqual(field["type"], schema.CHOICE)
        self.assertIn({"value": "new", "label": "New"}, field["choices"])

    def test_a_foreign_key_names_the_resource_it_points_at(self):
        field = self.field("projects", "lift")

        self.assertEqual(field["type"], schema.REFERENCE)
        self.assertEqual(field["related_resource"], "lifts")

    def test_a_collapsed_child_list_is_a_json_field(self):
        """Images, variants and specs are lists on the parent, not tables."""
        for resource_key, name in (
            ("lifts", "images"), ("lifts", "variants"), ("lifts", "specs"),
            ("projects", "images"),
        ):
            with self.subTest(field=f"{resource_key}.{name}"):
                self.assertEqual(self.field(resource_key, name)["type"], schema.JSON)

    def test_a_collapsed_category_is_a_choice_not_a_reference(self):
        """The category tables are gone; what is left is a choice on the row."""
        for resource_key in ("projects", "blogs", "gallery"):
            with self.subTest(resource=resource_key):
                self.assertEqual(
                    self.field(resource_key, "category")["type"], schema.CHOICE
                )

    def test_a_many_to_many_is_marked_as_such(self):
        self.assertEqual(self.field("lifts", "applications")["type"], schema.MULTI_REFERENCE)

    def test_a_hex_column_becomes_a_colour_picker(self):
        self.assertEqual(self.field("finishes", "swatch_hex")["type"], schema.COLOR)
        self.assertEqual(self.field("lifts", "accent")["type"], schema.COLOR)

    def test_long_prose_becomes_a_textarea_and_short_prose_an_input(self):
        self.assertEqual(self.field("lifts", "summary")["type"], schema.TEXT)
        self.assertEqual(self.field("lifts", "name")["type"], schema.STRING)

    def test_an_image_field_is_not_mistaken_for_a_plain_file(self):
        self.assertEqual(self.field("finishes", "texture")["type"], schema.IMAGE)

    def test_a_slug_knows_which_field_to_generate_from(self):
        field = self.field("lifts", "slug")

        self.assertEqual(field["type"], schema.SLUG)
        self.assertEqual(field["slug_source"], "name")

    def test_blank_false_makes_a_field_required(self):
        self.assertTrue(self.field("lifts", "name")["required"])
        self.assertFalse(self.field("lifts", "short_name")["required"])

    def test_a_readonly_field_is_never_required(self):
        """Otherwise the form would demand a value for an input it will not show."""
        for resource in registry:
            for field in schema.describe_resource(resource)["fields"]:
                if field["readonly"]:
                    with self.subTest(resource=resource.key, field=field["name"]):
                        self.assertFalse(field["required"])

    def test_help_text_is_carried_through(self):
        self.assertIn("cards", self.field("lifts", "summary")["help_text"])


class RequiredContractTests(AdminPanelTestCase):
    """The form's asterisks must match what the API actually demands.

    The schema and the serializer are built from the same model but by different
    code, so this is the seam where they could disagree — and a form that stars
    a field the server does not want is a form people fight with.
    """

    def test_schema_required_matches_the_serializer_for_every_resource(self):
        from apps.adminpanel.serializers import serializer_for

        for resource in registry:
            fields = serializer_for(resource)().fields
            for described in schema.describe_resource(resource)["fields"]:
                serializer_field = fields.get(described["name"])
                if serializer_field is None or serializer_field.read_only:
                    continue
                with self.subTest(resource=resource.key, field=described["name"]):
                    self.assertEqual(described["required"], serializer_field.required)

    def test_a_boolean_is_never_required(self):
        described = schema.describe_resource(registry["lifts"])
        for field in described["fields"]:
            if field["type"] == "boolean":
                with self.subTest(field=field["name"]):
                    self.assertFalse(field["required"])

    def test_a_field_with_a_model_default_is_optional(self):
        described = schema.describe_resource(registry["lifts"])
        by_name = {f["name"]: f for f in described["fields"]}

        self.assertFalse(by_name["order"]["required"])   # default=0
        self.assertTrue(by_name["name"]["required"])     # no default, blank=False


class ResourceViewSchemaTests(AdminPanelTestCase):
    def test_the_schema_endpoint_serves_the_same_description(self):
        body = self.get("/lifts/schema/")

        self.assertEqual(body["key"], "lifts")
        self.assertEqual(body["label_plural"], "Lifts")
        self.assertTrue(body["fields"])
        self.assertTrue(body["fieldsets"])

    def test_an_enquiry_form_still_shows_the_fields_it_cannot_edit(self):
        """Staff must be able to read the enquiry, not just its two writable fields."""
        body = self.get("/enquiries/schema/")
        shown = {name for section in body["fieldsets"] for name in section["fields"]}

        self.assertIn("name", shown)
        self.assertIn("message", shown)
        self.assertIn("status", shown)
        self.assertTrue(next(f for f in body["fields"] if f["name"] == "name")["readonly"])

    def test_permissions_are_reported_so_the_ui_can_hide_what_it_cannot_do(self):
        self.assertEqual(
            self.get("/enquiries/schema/")["permissions"],
            {"create": False, "edit": True, "delete": False},
        )
        self.assertEqual(
            self.get("/awards/schema/")["permissions"],
            {"create": True, "edit": True, "delete": True},
        )


class LabelTests(AdminPanelTestCase):
    """Labels keep the capitalisation their author chose."""

    def test_a_declared_plural_overrides_the_derived_one(self):
        """The sidebar heading already says "Knowledge base"; the link need not."""
        self.assertEqual(registry["knowledge-bases"].label_plural, "Knowledge base")

    def test_a_default_verbose_name_is_sentence_cased(self):
        self.assertEqual(registry["awards"].label_plural, "Awards")
        self.assertEqual(registry["testimonials"].label_plural, "Testimonials")

    def test_a_declared_label_is_used_verbatim(self):
        self.assertEqual(registry["blogs"].label_plural, "Blogs")
        self.assertEqual(registry["blogs"].label, "Blog post")

    def test_field_labels_follow_the_same_rule(self):
        described = schema.describe_resource(registry["lifts"])
        labels = {f["name"]: f["label"] for f in described["fields"]}

        self.assertEqual(labels["hero_image_url"], "Hero image url")
        self.assertEqual(labels["is_published"], "Is published")


class NavigationTests(AdminPanelTestCase):
    def test_navigation_returns_the_user_and_the_grouped_sidebar(self):
        body = self.get("/navigation/")

        self.assertEqual(body["user"]["email"], self.staff.email)
        self.assertTrue(body["user"]["is_staff"])

        groups = {g["group"] for g in body["groups"]}
        self.assertEqual(
            groups,
            {
                "Inbox",
                "Lifts",
                "Projects",
                "Blogs",
                "Editorial",
                "Site settings",
                "Knowledge base",
            },
        )

    def test_navigation_is_trimmed_of_field_detail(self):
        """First paint should not carry every field of every collection."""
        body = self.get("/navigation/")
        entry = body["groups"][0]["resources"][0]

        self.assertIn("label_plural", entry)
        self.assertNotIn("fields", entry)

    def test_navigation_lists_every_registered_resource_exactly_once(self):
        body = self.get("/navigation/")
        keys = [r["key"] for g in body["groups"] for r in g["resources"]]

        self.assertEqual(len(keys), len(registry))
        self.assertEqual(len(keys), len(set(keys)))
