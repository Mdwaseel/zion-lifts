"""What has to be true of a file before it becomes a document version.

Every check here runs in the request, before anything is stored and before any
job is queued, and none of them opens the PDF. Parsing is the worker's job:
a malformed document should cost one background retry, not a Django worker
blocked on someone else's 300-page scan.

The ordering is deliberate — cheapest and most conclusive first, so a wrong file
is rejected before its bytes are read at all.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata

from django.core.exceptions import ValidationError

# One format for now. A tuple rather than a constant because the next formats
# (DOCX, plain text) slot in here and nowhere else.
ALLOWED_EXTENSIONS = ("pdf",)
ALLOWED_MIME_TYPES = ("application/pdf", "application/x-pdf")

# Every PDF begins with this. Checked because Content-Type is supplied by the
# client and an extension is just the end of a string: neither is evidence of
# what the bytes are.
PDF_SIGNATURE = b"%PDF-"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MIN_UPLOAD_BYTES = len(PDF_SIGNATURE) + 1

# Read in blocks rather than whole: hashing a 25 MB upload should not also hold
# 25 MB of it in memory.
_HASH_BLOCK = 1024 * 1024

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")
_RESERVED_WINDOWS = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def sanitize_filename(raw: str) -> str:
    """A filename safe to store and safe to echo back.

    Path separators and traversal are removed rather than escaped: there is no
    legitimate upload whose name contains a directory, so anything that looks
    like one is a probe. The result is only ever used as a *label* — the real
    storage path is built from the document's UUID — but a name that reaches a
    log line, a download header and a control-room table should not need every
    one of those to defend itself.
    """
    name = unicodedata.normalize("NFKC", raw or "").strip()

    # Take the last segment under either separator, so "../../etc/passwd" and
    # "..\\..\\windows\\system32" both reduce to their final component.
    name = name.replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")
    name = _UNSAFE_NAME.sub("_", name).strip(". ")

    if not name:
        name = "upload.pdf"

    stem, dot, suffix = name.rpartition(".")
    if dot and stem.lower() in _RESERVED_WINDOWS:
        name = f"{stem}_file{dot}{suffix}"
    elif not dot and name.lower() in _RESERVED_WINDOWS:
        name = f"{name}_file"

    # Long enough for any real document, short enough for the column and for
    # every filesystem this might be stored on.
    if len(name) > 180:
        stem, dot, suffix = name.rpartition(".")
        keep = 180 - len(suffix) - 1 if dot else 180
        name = f"{stem[:keep]}{dot}{suffix}" if dot else name[:180]

    return name


def extension_of(filename: str) -> str:
    return os.path.splitext(filename)[1].lstrip(".").lower()


def hash_upload(upload) -> tuple[str, int]:
    """SHA-256 and byte length of an uploaded file, leaving it rewound.

    The hash is what makes a re-upload recognisable, so it is computed from the
    bytes rather than from anything the client said about them.
    """
    digest = hashlib.sha256()
    size = 0
    upload.seek(0)
    for block in iter(lambda: upload.read(_HASH_BLOCK), b""):
        digest.update(block)
        size += len(block)
    upload.seek(0)
    return digest.hexdigest(), size


def validate_upload(upload, *, max_bytes: int = MAX_UPLOAD_BYTES) -> dict:
    """Check an uploaded file and return what was learned about it.

    Raises ``ValidationError`` with a message an operator can act on. Returns
    ``{filename, extension, mime_type, content_hash, file_size}``.
    """
    if upload is None:
        raise ValidationError("A file is required.")

    filename = sanitize_filename(getattr(upload, "name", ""))
    extension = extension_of(filename)

    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(f".{e}" for e in ALLOWED_EXTENSIONS)
        raise ValidationError(f"Only {allowed} files can be uploaded (got {filename!r}).")

    # Checked but never trusted on its own — the signature below is the real
    # test. A mismatch here still means something is wrong worth reporting.
    declared = (getattr(upload, "content_type", "") or "").split(";")[0].strip().lower()
    if declared and declared not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"That file says it is {declared!r}; only PDF files can be uploaded."
        )

    size = getattr(upload, "size", None)
    if size is None:
        upload.seek(0, os.SEEK_END)
        size = upload.tell()
        upload.seek(0)

    if size == 0:
        raise ValidationError("That file is empty.")
    if size < MIN_UPLOAD_BYTES:
        raise ValidationError("That file is too small to be a PDF.")
    if size > max_bytes:
        raise ValidationError(
            f"That file is {size / 1024 / 1024:.1f} MB; the limit is "
            f"{max_bytes / 1024 / 1024:.0f} MB."
        )

    upload.seek(0)
    signature = upload.read(len(PDF_SIGNATURE))
    upload.seek(0)
    if signature != PDF_SIGNATURE:
        raise ValidationError(
            "That file is not a PDF. Its name says .pdf but its contents do not."
        )

    content_hash, hashed_size = hash_upload(upload)

    return {
        "filename": filename,
        "extension": extension,
        "mime_type": declared or "application/pdf",
        "content_hash": content_hash,
        "file_size": hashed_size,
    }
