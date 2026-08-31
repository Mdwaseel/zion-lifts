"""What gets in, and what does not.

These are the checks that stand between an anonymous byte stream and the
filesystem, so each one is tested against the thing it is actually defending
against rather than against a well-behaved input.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.knowledge.validators import (
    MAX_UPLOAD_BYTES,
    hash_upload,
    sanitize_filename,
    validate_upload,
)

from .base import MINIMAL_PDF, big_pdf, raw_upload


class FilenameSanitisationTests(SimpleTestCase):
    def test_a_normal_name_is_left_alone(self):
        self.assertEqual(sanitize_filename("Warranty Policy 2026.pdf"), "Warranty Policy 2026.pdf")

    def test_posix_traversal_is_reduced_to_the_final_component(self):
        self.assertEqual(sanitize_filename("../../../etc/passwd"), "passwd")

    def test_windows_traversal_is_reduced_too(self):
        self.assertEqual(
            sanitize_filename("..\\..\\windows\\system32\\config.pdf"), "config.pdf"
        )

    def test_an_absolute_path_keeps_only_its_name(self):
        self.assertEqual(sanitize_filename("/var/www/secret.pdf"), "secret.pdf")

    def test_null_bytes_are_removed(self):
        self.assertNotIn("\x00", sanitize_filename("evil\x00.pdf"))

    def test_shell_and_markup_characters_are_replaced(self):
        cleaned = sanitize_filename("re;port <script>.pdf")
        for char in ";<>":
            self.assertNotIn(char, cleaned)

    def test_a_name_of_only_dots_does_not_become_empty(self):
        self.assertTrue(sanitize_filename("..."))
        self.assertTrue(sanitize_filename(""))

    def test_windows_reserved_names_are_defused(self):
        # CON.pdf is not openable on Windows; storing one makes a document that
        # can never be read back on half the machines this might run on.
        self.assertNotEqual(sanitize_filename("CON.pdf").lower(), "con.pdf")
        self.assertNotEqual(sanitize_filename("nul").lower(), "nul")

    def test_very_long_names_are_trimmed_but_keep_their_extension(self):
        cleaned = sanitize_filename("a" * 500 + ".pdf")
        self.assertLessEqual(len(cleaned), 180)
        self.assertTrue(cleaned.endswith(".pdf"))


class UploadValidationTests(SimpleTestCase):
    def test_a_real_pdf_is_accepted_and_described(self):
        facts = validate_upload(raw_upload("policy.pdf", MINIMAL_PDF))
        self.assertEqual(facts["filename"], "policy.pdf")
        self.assertEqual(facts["extension"], "pdf")
        self.assertEqual(facts["file_size"], len(MINIMAL_PDF))
        self.assertEqual(len(facts["content_hash"]), 64)

    def test_a_missing_file_is_refused(self):
        with self.assertRaises(ValidationError):
            validate_upload(None)

    def test_a_wrong_extension_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            validate_upload(raw_upload("notes.txt", MINIMAL_PDF, "text/plain"))
        self.assertIn(".pdf", str(caught.exception))

    def test_a_wrong_declared_mime_type_is_refused(self):
        with self.assertRaises(ValidationError):
            validate_upload(raw_upload("policy.pdf", MINIMAL_PDF, "application/zip"))

    def test_an_empty_file_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            validate_upload(raw_upload("policy.pdf", b""))
        self.assertIn("empty", str(caught.exception).lower())

    def test_a_file_that_only_claims_to_be_a_pdf_is_refused(self):
        # The whole point of reading the signature: the name says .pdf and the
        # Content-Type agrees, and the bytes are an ELF binary.
        with self.assertRaises(ValidationError) as caught:
            validate_upload(raw_upload("payload.pdf", b"\x7fELF" + b"\x00" * 200))
        self.assertIn("not a PDF", str(caught.exception))

    def test_an_html_file_renamed_to_pdf_is_refused(self):
        with self.assertRaises(ValidationError):
            validate_upload(raw_upload("page.pdf", b"<html><body>hi</body></html>"))

    def test_an_oversized_file_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            validate_upload(raw_upload("huge.pdf", big_pdf(MAX_UPLOAD_BYTES + 1024)))
        self.assertIn("limit", str(caught.exception))

    def test_a_traversal_filename_is_accepted_but_neutralised(self):
        # The file itself is fine; only its name was hostile. It should be
        # stored under a safe name rather than rejected.
        facts = validate_upload(raw_upload("../../etc/passwd.pdf", MINIMAL_PDF))
        self.assertEqual(facts["filename"], "passwd.pdf")

    def test_validation_leaves_the_file_rewound(self):
        upload = raw_upload("policy.pdf", MINIMAL_PDF)
        validate_upload(upload)
        # The service stores this same handle immediately afterwards; a
        # consumed stream would be written as an empty file.
        self.assertEqual(upload.read(), MINIMAL_PDF)


class ContentHashTests(SimpleTestCase):
    def test_identical_bytes_hash_identically(self):
        first, size_a = hash_upload(raw_upload("a.pdf", MINIMAL_PDF))
        second, size_b = hash_upload(raw_upload("b.pdf", MINIMAL_PDF))
        self.assertEqual(first, second)
        self.assertEqual(size_a, size_b)

    def test_one_changed_byte_changes_the_hash(self):
        first, _ = hash_upload(raw_upload("a.pdf", MINIMAL_PDF))
        second, _ = hash_upload(raw_upload("a.pdf", MINIMAL_PDF + b" "))
        self.assertNotEqual(first, second)

    def test_hashing_leaves_the_file_rewound(self):
        upload = raw_upload("a.pdf", MINIMAL_PDF)
        hash_upload(upload)
        self.assertEqual(upload.read(), MINIMAL_PDF)
