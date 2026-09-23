"""Uploading a picture from a computer, and what the form is told about it.

Two halves. The endpoint has to accept real files, refuse everything else, and
never trust what the client says a file is. The schema has to mark the right
fields as media, because that is what decides whether an operator sees an
uploader or a text box asking for a path.
"""

from __future__ import annotations

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.adminpanel import schema, uploads
from apps.adminpanel.registry import registry

from .base import API, AdminPanelTestCase

# Real leading bytes. A file whose header says something else is exactly what
# these tests are here to catch, so the fixtures have to be honest.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 64
MP4 = b"\x00\x00\x00\x18" + b"ftyp" + b"isom" + b"\x00" * 64
GIF = b"GIF89a" + b"\x00" * 64

_MEDIA = tempfile.mkdtemp(prefix="zion-upload-tests-")


@override_settings(MEDIA_ROOT=_MEDIA)
class UploadTestCase(AdminPanelTestCase):
    """Writes into a temporary MEDIA_ROOT, so a test run leaves no files behind."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def upload(self, name, content, *, client=None, expect=201, folder="projects"):
        res = (client or self.client).post(
            f"{API}/uploads/",
            {"file": SimpleUploadedFile(name, content), "folder": folder},
            format="multipart",
        )
        self.assertEqual(
            res.status_code, expect, f"upload {name} -> {res.status_code} {res.content[:200]}"
        )
        return res.json() if res.content else {}


class EndpointTests(UploadTestCase):
    def test_an_image_can_be_uploaded_and_answers_with_its_url(self):
        body = self.upload("hero.png", PNG)

        self.assertTrue(body["url"].startswith("/uploads/"))
        self.assertEqual(body["kind"], "image")
        self.assertEqual(body["name"], "hero.png")
        self.assertEqual(body["size"], len(PNG))

    def test_every_supported_image_format_is_accepted(self):
        for name, content in (
            ("a.png", PNG), ("b.jpg", JPEG), ("c.jpeg", JPEG),
            ("d.webp", WEBP), ("e.gif", GIF),
        ):
            with self.subTest(file=name):
                self.assertEqual(self.upload(name, content)["kind"], "image")

    def test_a_video_is_accepted_and_reported_as_one(self):
        self.assertEqual(self.upload("film.mp4", MP4)["kind"], "video")

    def test_the_stored_path_is_not_the_uploaded_name(self):
        """Two people uploading "hero.png" must not collide, or overwrite."""
        first = self.upload("hero.png", PNG)["url"]
        second = self.upload("hero.png", PNG)["url"]

        self.assertNotEqual(first, second)
        self.assertNotIn("hero", first)
        self.assertTrue(first.endswith(".png"))

    def test_the_folder_sorts_uploads_by_collection(self):
        self.assertIn("/projects/", self.upload("a.png", PNG, folder="projects")["url"])
        self.assertIn("/lifts/", self.upload("b.png", PNG, folder="lifts")["url"])

    def test_a_folder_cannot_escape_the_uploads_directory(self):
        """It reaches a filesystem path, so traversal must not survive it."""
        url = self.upload("a.png", PNG, folder="../../etc")["url"]

        self.assertNotIn("..", url)
        self.assertTrue(url.startswith("/uploads/"))


class RefusalTests(UploadTestCase):
    def test_a_request_with_no_file_is_a_bad_request(self):
        res = self.client.post(f"{API}/uploads/", {}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_an_unsupported_type_is_refused(self):
        body = self.upload("notes.txt", b"hello", expect=400)
        self.assertIn("not supported", body["detail"])

    def test_an_empty_file_is_refused(self):
        self.upload("empty.png", b"", expect=400)

    def test_an_executable_renamed_as_an_image_is_refused(self):
        """The extension is the end of a string; the bytes are the evidence."""
        body = self.upload("payload.png", b"MZ\x90\x00" + b"\x00" * 64, expect=400)
        self.assertIn("does not look like", body["detail"])

    def test_a_pdf_renamed_as_a_jpeg_is_refused(self):
        self.upload("scan.jpg", b"%PDF-1.7\n" + b"\x00" * 64, expect=400)

    def test_a_declared_content_type_does_not_override_the_bytes(self):
        """Content-Type is supplied by the client, so it decides nothing."""
        res = self.client.post(
            f"{API}/uploads/",
            {
                "file": SimpleUploadedFile(
                    "fake.png", b"not an image at all", content_type="image/png"
                )
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)

    def test_an_oversized_image_is_refused(self):
        oversized = PNG + b"\x00" * (uploads.MAX_IMAGE_BYTES + 1)
        body = self.upload("huge.png", oversized, expect=400)
        self.assertIn("limit", body["detail"])

    def test_a_video_may_be_larger_than_an_image(self):
        """A film is legitimately bigger; one limit for both would be wrong."""
        self.assertGreater(uploads.MAX_VIDEO_BYTES, uploads.MAX_IMAGE_BYTES)


class PermissionTests(UploadTestCase):
    def test_an_anonymous_caller_cannot_upload(self):
        """An open upload endpoint is a free file host."""
        res = self.as_anonymous().post(
            f"{API}/uploads/", {"file": SimpleUploadedFile("a.png", PNG)}, format="multipart"
        )
        self.assertEqual(res.status_code, 401)

    def test_a_signed_in_non_staff_user_cannot_upload(self):
        res = self.as_non_staff().post(
            f"{API}/uploads/", {"file": SimpleUploadedFile("a.png", PNG)}, format="multipart"
        )
        self.assertEqual(res.status_code, 403)


class SchemaTests(AdminPanelTestCase):
    """What the form is told, which is what decides the control it renders."""

    def field(self, resource_key, name):
        described = schema.describe_resource(registry[resource_key])
        return next(f for f in described["fields"] if f["name"] == name)

    def test_a_picture_field_is_media_rather_than_a_text_box(self):
        for resource_key, name in (
            ("projects", "hero_image_url"), ("projects", "poster_url"),
            ("lifts", "hero_image_url"), ("gallery", "image_url"),
            ("team", "photo_url"), ("partners", "logo_url"),
            ("finishes", "texture_url"), ("applications", "image_url"),
            ("blogs", "hero_image_url"), ("awards", "image_url"),
        ):
            with self.subTest(field=f"{resource_key}.{name}"):
                described = self.field(resource_key, name)
                self.assertEqual(described["type"], schema.MEDIA)
                self.assertEqual(described["media_kind"], "image")
                self.assertEqual(described["upload_folder"], resource_key)

    def test_a_film_field_is_media_of_the_video_kind(self):
        for resource_key, name in (
            ("projects", "hero_video_url"), ("projects", "loop_video_url"),
            ("lifts", "hero_video_url"), ("testimonials", "video_url"),
            ("safety-features", "media_url"),
        ):
            with self.subTest(field=f"{resource_key}.{name}"):
                described = self.field(resource_key, name)
                self.assertEqual(described["type"], schema.MEDIA)
                self.assertEqual(described["media_kind"], "video")

    def test_a_link_to_somebody_elses_site_is_still_a_url(self):
        """An uploader would be nonsense on a map embed or a partner's website."""
        for resource_key, name in (
            ("offices", "map_embed_url"), ("offices", "directions_url"),
            ("partners", "website"),
        ):
            with self.subTest(field=f"{resource_key}.{name}"):
                self.assertEqual(self.field(resource_key, name)["type"], schema.URL)

    def test_a_list_of_photographs_describes_its_own_rows(self):
        for resource_key in ("projects", "lifts"):
            with self.subTest(resource=resource_key):
                described = self.field(resource_key, "images")

                self.assertEqual(described["type"], schema.MEDIA_LIST)
                self.assertEqual(described["src_key"], "src")
                names = {item["name"] for item in described["fields"]}
                self.assertTrue({"alt", "caption"} <= names)

    def test_each_model_gets_the_row_shape_its_own_data_uses(self):
        """The two `images` columns are not the same shape.

        A lift's photographs are tagged by where they belong on the product page
        (`kind`); a project's by how far through the installation they were
        taken (`stage`). One shared schema would put an irrelevant dropdown on
        every row of both.
        """
        lift = {item["name"]: item for item in self.field("lifts", "images")["fields"]}
        project = {item["name"]: item for item in self.field("projects", "images")["fields"]}

        self.assertIn("kind", lift)
        self.assertNotIn("stage", lift)
        self.assertIn("stage", project)
        self.assertNotIn("kind", project)

    def test_the_row_tag_offers_the_values_the_site_actually_renders(self):
        """A free-text box is how a typo becomes a photograph nobody ever sees."""
        lift_kind = next(
            item for item in self.field("lifts", "images")["fields"] if item["name"] == "kind"
        )
        self.assertEqual(lift_kind["type"], schema.CHOICE)
        self.assertEqual(
            {choice["value"] for choice in lift_kind["choices"]},
            {"gallery", "detail", "cabin"},
        )

    def test_a_json_field_that_is_not_media_stays_json(self):
        """Variants and specs are tables of text, not pictures."""
        for name in ("variants", "specs"):
            with self.subTest(field=name):
                self.assertEqual(self.field("lifts", name)["type"], schema.JSON)

    def test_the_duplicate_legacy_image_field_is_not_in_the_form(self):
        """Two controls for one photograph, and no way to know which wins."""
        for resource_key, name in (
            ("gallery", "image"), ("team", "photo"),
            ("partners", "logo"), ("finishes", "texture"),
        ):
            with self.subTest(field=f"{resource_key}.{name}"):
                described = schema.describe_resource(registry[resource_key])
                self.assertNotIn(name, {f["name"] for f in described["fields"]})


class SavingTests(UploadTestCase):
    """The uploaded URL goes into the record like any other string."""

    def test_an_uploaded_url_can_be_saved_onto_a_record(self):
        url = self.upload("hero.png", PNG, folder="lifts")["url"]
        body = self.post(
            "/lifts/",
            {"slug": "test-lift", "name": "Test", "tagline": "t", "summary": "s",
             "hero_image_url": url},
        )
        self.assertEqual(body["hero_image_url"], url)

    def test_a_list_of_photographs_saves_as_the_json_it_always_was(self):
        first = self.upload("a.png", PNG, folder="projects")["url"]
        second = self.upload("b.png", PNG, folder="projects")["url"]

        body = self.post(
            "/projects/",
            {
                "slug": "test-project", "name": "Test", "location": "Hyderabad",
                "images": [
                    {"stage": "interior", "src": first, "alt": "One", "caption": ""},
                    {"stage": "exterior", "src": second, "alt": "Two", "caption": ""},
                ],
            },
        )
        self.assertEqual([row["src"] for row in body["images"]], [first, second])
