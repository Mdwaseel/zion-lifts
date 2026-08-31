# -*- coding: utf-8 -*-
"""Source the imagery Zion has no photograph for, from Openverse (CC-licensed).

Every download keeps its licence and creator so ATTRIBUTION.md can be generated.
These are stand-ins: anything marked `swap=True` should be replaced with a real
Zion shoot before launch. Run with `--force` to re-fetch.
"""
import argparse
import io
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "media" / "sourced"
MANIFEST = ROOT / "assets-src" / "sourced-manifest.json"
API = "https://api.openverse.org/v1/images/"
UA = "ZionLiftsSiteBuild/1.0 (asset pipeline; contact: info@zionlifts.com)"

# slug, search query, minimum long edge, needs-a-real-Zion-shoot
WANTED = [
    # --- lift types Zion has no photograph of yet ---------------------------
    ("lift-freight",        "freight elevator industrial",         1200, True),
    ("lift-freight-2",      "goods lift warehouse",                1100, True),
    ("lift-hospital",       "hospital elevator corridor",          1200, True),
    ("lift-hospital-2",     "hospital interior hallway modern",    1400, True),
    ("lift-platform",       "wheelchair platform lift accessibility", 900, True),
    ("lift-platform-2",     "accessible ramp lift building",       1000, True),

    # --- the making of Zion / inside the factory ----------------------------
    ("factory-fabrication", "metal fabrication workshop",          1400, True),
    ("factory-sheetmetal",  "sheet metal press brake factory",     1200, True),
    ("factory-machining",   "cnc machining metal lathe",           1400, True),
    ("factory-welding",     "welding sparks metal worker",         1400, True),
    ("factory-assembly",    "factory assembly line workers",       1400, True),
    ("factory-floor",       "industrial factory interior machines", 1600, True),
    ("factory-dispatch",    "warehouse loading dispatch crates",   1200, True),

    # --- the engineering: macro component photography -----------------------
    ("macro-motor",         "electric motor detail closeup",       1200, True),
    ("macro-gears",         "gears machine detail macro",          1200, True),
    ("macro-rope",          "steel wire rope cable closeup",       1200, True),
    ("macro-bearing",       "ball bearing metal macro",            1000, True),
    ("macro-controller",    "electrical control panel wiring",     1200, True),
    ("macro-circuit",       "circuit board electronics macro",     1200, True),
    ("macro-sensor",        "industrial sensor electronics",       1000, True),
    ("macro-brake",         "brake disc mechanism metal",          1000, True),

    # --- the people ---------------------------------------------------------
    ("people-engineer",     "engineer technician working portrait", 1200, True),
    ("people-hands",        "worker hands tools working closeup",   1200, True),
    ("people-electrician",  "electrician working control panel",    1200, True),
    ("people-team",         "engineers team site meeting helmet",   1200, True),
    ("people-site",         "construction site engineer blueprint", 1200, True),
    ("people-drafting",     "architect drafting technical drawing", 1200, True),

    # --- the world below: building contexts ---------------------------------
    ("context-villa",       "modern villa interior staircase",     1400, False),
    ("context-apartment",   "apartment building lobby interior",   1400, False),
    ("context-hotel",       "hotel lobby luxury interior",         1600, False),
    ("context-office",      "office building lobby modern",        1600, False),
    ("context-hospital",    "hospital lobby interior modern",      1400, False),
    ("context-industrial",  "industrial warehouse interior",       1400, False),

    # --- closing plates -----------------------------------------------------
    ("skyline-city",        "city skyline dusk aerial",            1800, False),
    ("skyline-hyderabad",   "hyderabad city skyline",              1400, False),
    ("blueprint-technical", "architectural blueprint technical drawing", 1400, False),
    ("architecture-facade", "modern building facade architecture", 1600, False),
]

WIDTHS = [640, 1280, 1920]


def _page(query, page):
    params = urllib.parse.urlencode(
        {
            "q": query,
            "page": page,
            "page_size": 20,
            "license_type": "all-cc,commercial,modification",
            "mature": "false",
        }
    )
    req = urllib.request.Request(API + "?" + params, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r).get("results", [])


def search(query, min_edge):
    """Collect candidates across two pages, widest and most permissive first.

    No `category` filter: it pins results to Flickr, whose files cap at 1024px
    and so fail the size gate for every hero-sized asset we need.
    """
    items = []
    for page in (1, 2):
        try:
            items += _page(query, page)
        except Exception:
            break
    out = [
        i for i in items
        if i.get("url") and max(i.get("width") or 0, i.get("height") or 0) >= min_edge
    ]
    if not out:  # size gate too tight for this subject — take what exists
        out = [i for i in items if i.get("url")]
    rank = {"cc0": 0, "pdm": 0, "by": 1, "by-sa": 2}
    out.sort(key=lambda i: (rank.get(i.get("license", ""), 3), -(i.get("width") or 0)))
    return out


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def emit(raw, slug):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for w in WIDTHS:
        if w > im.width * 1.05:
            continue
        h = round(im.height * w / im.width)
        im.resize((w, h), Image.LANCZOS).save(
            OUT / f"{slug}-{w}.webp", "WEBP", quality=80, method=6
        )
        made.append(w)
    fw = made[-1] if made else im.width
    im.resize((fw, round(im.height * fw / im.width)), Image.LANCZOS).save(
        OUT / f"{slug}.jpg", "JPEG", quality=82, optimize=True, progressive=True
    )
    return made, im.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    manifest = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for slug, query, min_edge, swap in WANTED:
        if args.only and args.only not in slug:
            continue
        if slug in manifest and not args.force and (OUT / f"{slug}.jpg").exists():
            print(f"  = {slug}")
            continue
        try:
            candidates = search(query, min_edge)
        except Exception as e:
            print(f"  ! {slug}: search failed ({e})")
            continue
        saved = False
        for item in candidates[:6]:
            try:
                raw = download(item["url"])
                made, size = emit(raw, slug)
            except Exception:
                continue
            manifest[slug] = {
                "query": query,
                "title": item.get("title") or "",
                "creator": item.get("creator") or "Unknown",
                "creator_url": item.get("creator_url") or "",
                "license": (item.get("license") or "").upper(),
                "license_version": item.get("license_version") or "",
                "license_url": item.get("license_url") or "",
                "source": item.get("source") or "",
                "foreign_landing_url": item.get("foreign_landing_url") or "",
                "widths": made,
                "native": list(size),
                "replace_with_real_shoot": swap,
            }
            print(f"  + {slug}: {item.get('license','').upper()} {size[0]}x{size[1]} {made}")
            saved = True
            break
        if not saved:
            print(f"  ! {slug}: nothing usable for '{query}'")
        time.sleep(0.4)

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(manifest)} sourced assets -> {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
