# -*- coding: utf-8 -*-
"""Find /media/... paths referenced in code or seed data that no longer exist."""
import pathlib
import re

ROOT = pathlib.Path(r"d:\Projects\Zion Lifts")
MEDIA = ROOT / "frontend" / "public" / "media"

existing = {
    p.relative_to(MEDIA).as_posix() for p in MEDIA.rglob("*") if p.is_file()
}

sources = (
    list((ROOT / "frontend" / "src").rglob("*.jsx"))
    + list((ROOT / "frontend" / "src").rglob("*.js"))
    + list((ROOT / "backend" / "apps").rglob("*.py"))
)

pat = re.compile(r"""["'](/media/[A-Za-z0-9._/\-]+)["']""")
refs = {}
for f in sources:
    for m in pat.finditer(f.read_text(encoding="utf-8", errors="replace")):
        refs.setdefault(m.group(1), set()).add(f.relative_to(ROOT).as_posix())

missing = {r: fs for r, fs in refs.items() if r[len("/media/"):] not in existing}
print(f"{len(refs)} distinct /media references, {len(missing)} missing\n")
for ref, files in sorted(missing.items()):
    print(" ", ref)
    for f in sorted(files):
        print("     <-", f)

# seeded URLs live in the database too
import os, sys, django
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zion.settings")
django.setup()

from apps.catalog.models import LiftImage, LiftType          # noqa: E402
from apps.content.models import Award, GalleryItem, JournalPost, Milestone, TeamMember  # noqa: E402
from apps.projects.models import Project, ProjectImage       # noqa: E402

db_missing = []


def check(label, value):
    if value and value.startswith("/media/") and value[len("/media/"):] not in existing:
        db_missing.append((label, value))


for lift in LiftType.objects.all():
    check(f"LiftType {lift.slug}.hero", lift.hero_image_url)
    check(f"LiftType {lift.slug}.video", lift.hero_video_url)
for img in LiftImage.objects.all():
    check(f"LiftImage {img.lift_type.slug}/{img.kind}", img.image_url)
for p in Project.objects.all():
    for field in ("hero_image_url", "hero_video_url", "loop_video_url", "poster_url"):
        check(f"Project {p.slug}.{field}", getattr(p, field))
for img in ProjectImage.objects.all():
    check(f"ProjectImage {img.project.slug}/{img.stage}", img.image_url)
for g in GalleryItem.objects.all():
    check(f"Gallery #{g.pk}", g.image_url)
for m in Milestone.objects.all():
    check(f"Milestone {m.year}", m.image_url)
for t in TeamMember.objects.all():
    check(f"Team {t.name}", t.photo_url)
for a in Award.objects.all():
    check(f"Award {a.year}", a.image_url)
for j in JournalPost.objects.all():
    check(f"Journal {j.slug}", j.hero_image_url)

print(f"\ndatabase: {len(db_missing)} missing")
for label, value in db_missing:
    print("  ", label, "->", value)
