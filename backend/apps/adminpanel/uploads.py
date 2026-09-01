"""Accepting a picture or a film from somebody's computer.

The control room used to ask for a *path* — you typed ``/media/frames/foo.jpg``
into a text box and hoped it existed. That is a developer's interface: it
assumes you know what is already on the server, it cannot tell you when you are
wrong, and there is nothing an operator with a photograph on their laptop can do
with it. This module is what replaces it.

**Why the fields still store a string.** A media field on these models is a
``CharField`` holding a URL, not Django's ``ImageField``. That has not changed
and does not need to: the upload lands here, the file is stored, and what goes
back into the record is the URL of what was stored. So nothing about the
database, the serializers or the public API moves — the site keeps reading the
same key — and the seeded catalogue, whose images live under the front end's own
``/media/`` tree rather than in this app's uploads, keeps rendering exactly as
it did. The change is entirely in how a person puts a value there.

**On trust.** Every check runs before a byte is written, cheapest first, and
none of them believes the client. The declared content type is a hint the
browser supplies; the extension is the end of a string. What decides is the
file's own leading bytes, because that is the only part of an upload the
uploader cannot simply relabel.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.knowledge.validators import sanitize_filename

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 64 * 1024 * 1024

# Extension -> (kind, magic prefixes). A format with no signature we can check
# does not belong on this list, however convenient it would be.
#
# The signatures are deliberately short and at a fixed offset. Anything longer
# starts encoding a parser, and this is a gate, not a decoder.
IMAGE_TYPES = {
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "gif": (b"GIF87a", b"GIF89a"),
    "webp": (b"RIFF",),  # plus "WEBP" at offset 8, checked below
    "avif": (b"",),      # checked via the ISO-BMFF brand at offset 4
}

VIDEO_TYPES = {
    "mp4": (b"",),   # ISO-BMFF, brand-checked
    "webm": (b"\x1a\x45\xdf\xa3",),
    "mov": (b"",),   # ISO-BMFF, brand-checked
}

# ISO base media files (mp4/mov/avif) all carry "ftyp" at offset 4; the four
# bytes after it name the brand. This is how one check covers three formats
# without shipping a container parser.
ISO_BMFF_AT_4 = b"ftyp"

HEADER_BYTES = 32


class UploadRejected(ValidationError):
    """The file cannot be accepted. The view turns this into a 400."""


@dataclass(frozen=True)
class StoredUpload:
    """What the panel needs to put the result into a field and show it."""

    url: str
    name: str
    size: int
    kind: str

    def as_dict(self) -> dict:
        return {"url": self.url, "name": self.name, "size": self.size, "kind": self.kind}


def store(upload, *, folder: str = "content") -> StoredUpload:
    """Validate an uploaded file and write it. Returns where it landed.

    ``folder`` is a caller-chosen bucket ("lifts", "projects"), sanitised here
    rather than trusted: it reaches a filesystem path, and the one thing a path
    segment must never be able to say is "go up a level".
    """
    name = sanitize_filename(getattr(upload, "name", "") or "upload")
    suffix = PurePosixPath(name).suffix.lower().lstrip(".")

    kind = _kind_for(suffix)
    _check_size(upload, kind)
    _check_signature(upload, suffix, kind)

    # Stored under a uuid, keeping only the extension. Two people uploading
    # "hero.jpg" must not collide, and the original name is a label rather than
    # an instruction — echoing it into a path is how traversal and overwrite
    # bugs get in, however carefully it was sanitised first.
    stem = uuid.uuid4().hex
    today = timezone.localdate()
    path = f"{_safe_folder(folder)}/{today:%Y/%m}/{stem}.{suffix}"

    stored_path = default_storage.save(path, upload)
    return StoredUpload(
        url=default_storage.url(stored_path),
        name=name,
        size=getattr(upload, "size", 0) or 0,
        kind=kind,
    )


def _kind_for(suffix: str) -> str:
    if suffix in IMAGE_TYPES:
        return "image"
    if suffix in VIDEO_TYPES:
        return "video"
    allowed = ", ".join(sorted({*IMAGE_TYPES, *VIDEO_TYPES}))
    raise UploadRejected(f"That file type is not supported. Allowed: {allowed}.")


def _check_size(upload, kind: str) -> None:
    size = getattr(upload, "size", 0) or 0
    if size <= 0:
        raise UploadRejected("That file is empty.")

    limit = MAX_IMAGE_BYTES if kind == "image" else MAX_VIDEO_BYTES
    if size > limit:
        raise UploadRejected(
            f"That file is {size / 1024 / 1024:.1f} MB; the limit for "
            f"{'an image' if kind == 'image' else 'a video'} is {limit // 1024 // 1024} MB."
        )


def _check_signature(upload, suffix: str, kind: str) -> None:
    """Confirm the bytes are what the extension claims.

    The stream is rewound afterwards, because the caller is about to store it
    and a file read to its header and never seeked back saves a truncated copy —
    a bug that only shows up as a corrupt image days later.
    """
    try:
        upload.seek(0)
        header = upload.read(HEADER_BYTES)
    finally:
        upload.seek(0)

    if _matches(header, suffix):
        return

    raise UploadRejected(
        f"That file does not look like {'an' if suffix[0] in 'aeiou' else 'a'} "
        f"{suffix.upper()} {kind}. Check the file and try again."
    )


def _matches(header: bytes, suffix: str) -> bool:
    if len(header) < 12:
        return False

    # ISO base media: mp4, mov and avif all identify themselves the same way.
    if suffix in {"mp4", "mov", "avif"}:
        return header[4:8] == ISO_BMFF_AT_4

    if suffix == "webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"

    signatures = IMAGE_TYPES.get(suffix) or VIDEO_TYPES.get(suffix) or ()
    return any(sig and header.startswith(sig) for sig in signatures)


def _safe_folder(folder: str) -> str:
    """One lowercase path segment, or "content" if the caller offered nonsense."""
    cleaned = "".join(ch for ch in (folder or "").lower() if ch.isalnum() or ch in "-_")
    return cleaned[:40] or "content"
