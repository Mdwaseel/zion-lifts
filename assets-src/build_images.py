# -*- coding: utf-8 -*-
"""Optimise Zion source imagery into responsive webp/jpg sets for the React app."""
import pathlib
from PIL import Image, ImageOps

ROOT = pathlib.Path(r"d:\Projects\Zion Lifts")
PUB  = ROOT / "frontend" / "public" / "media"

WIDTHS = [480, 960, 1600, 2400]

def emit(src: pathlib.Path, out_dir: pathlib.Path, slug: str, widths=WIDTHS, cover=None,
         upscale=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", im.size, (12, 12, 12))
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if cover:
        im = ImageOps.fit(im, cover, Image.LANCZOS, centering=(0.5, 0.45))
    made = []
    for w in widths:
        if w > im.width * 1.05 and not upscale:
            continue
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS)
        r.save(out_dir / f"{slug}-{w}.webp", "WEBP", quality=82, method=6)
        made.append(w)
    # jpg fallback at the largest emitted width
    fw = made[-1] if made else im.width
    fh = round(im.height * fw / im.width)
    im.resize((fw, fh), Image.LANCZOS).save(out_dir / f"{slug}.jpg", "JPEG",
                                            quality=84, optimize=True, progressive=True)
    print(f"  {slug}: {made} ({im.width}x{im.height} source)")
    return made


def main():
    # ---- 1. Luxury installation photography (10) --------------------------
    src = ROOT / "Zion HD Photos - Generated"
    # Named renders are emitted under their own slug. They are excluded from the
    # numbered set because the sort key reads digits out of the stem, so a file
    # without any would sort to the front and renumber every interior after it.
    NAMED = {"lift-chatgpt-generated": (PUB / "cabin", "cabin-hero")}
    files = sorted(
        (f for f in src.glob("*.png") if f.stem not in NAMED),
        key=lambda p: int("".join(c for c in p.stem if c.isdigit()) or 0),
    )
    print("interiors:")
    for i, f in enumerate(files, 1):
        emit(f, PUB / "interiors", f"interior-{i:02d}")
    # The configurator hero. Its source is only 1024 wide, but `cabin` declares a
    # 1600 step in lib/media.js — without the upscale that entry 404s and the
    # SPA fallback serves index.html into an <img>. Upscaling a smooth render is
    # cheaper than teaching the srcset helper about per-file widths.
    for stem, (out, slug) in NAMED.items():
        f = src / f"{stem}.png"
        if f.exists():
            print(f"{slug}:")
            emit(f, out, slug, widths=[480, 960, 1600], upscale=True)

    # ---- 2. Product renders ----------------------------------------------
    groups = {
        "capsule": "Zion Website/Capsule",
        "car-stacker": "Zion Website/Car Stacker Lift",
        "dumbwaiter": "Zion Website/Dumb Waiter",
    }
    for slug, rel in groups.items():
        d = ROOT / rel
        seen = set()
        n = 0
        print(f"{slug}:")
        for f in sorted(d.glob("*.png")):
            key = f.stem.split("_")[2] if f.stem.count("_") >= 2 else f.stem
            if key in seen:
                continue
            seen.add(key)
            n += 1
            emit(f, PUB / "products", f"{slug}-{n:02d}")

    # ---- 2b. Building contexts -------------------------------------------
    # One render per context in the "Every building has a different rhythm"
    # section, keyed to the CONTEXTS slugs in pages/home/Ascent.jsx.
    contexts = {
        "villa": "Villa",
        "apartment": "Apartment",
        "hotel": "Hospitality",
        "office": "Office",
        "hospital": "Hospital",
        "industrial": "Industrial",
    }
    cd = ROOT / "Zion Website" / "section 1"
    if cd.is_dir():
        print("contexts:")
        for slug, stem in contexts.items():
            f = cd / f"{stem}.png"
            if f.exists():
                emit(f, PUB / "contexts", f"context-{slug}")

    # ---- 2f. Configurator finishes ---------------------------------------
    # One cabin render per selectable finish, keyed `<category>-<slug>` so the
    # configurator can derive a path from a choice without a lookup table. The
    # slugs are the finishes API's own; the file names are the photographer's.
    FINISHES = {
        "ceiling": {
            "perimete cove f": "light-cove",
            "recessed spots": "light-spots",
            "star lights": "light-starlight",
            "linear channel": "light-linear",
        },
        "wall finish": {
            "stainless steel": "material-brushed-steel",
            "antique brass": "material-antique-brass",
            "rose gold mirror": "material-rose-gold",
            "walnut veneer": "material-walnut",
            "stone laminate": "material-stone-grey",
        },
        "Flooring": {
            "granite": "floor-granite",
            "marble": "floor-marble",
            "vinyl": "floor-vinyl",
            "steel chequer plate": "floor-chequer",
        },
        "Touch Panels": {
            "steel": "control-brushed-cop",
            "capacitive touch": "control-touch-cop",
            "Braille": "control-braille-cop",
        },
        "lift doors": {
            "two door lift": "door-centre-auto",
            "side collapse lift": "door-side-auto",
            "glass automatic lift": "door-glass-auto",
            "manual grill": "door-manual-swing",
        },
    }
    print("finishes:")
    for folder, names in FINISHES.items():
        d = ROOT / "Zion Website" / folder
        for stem, slug in names.items():
            f = d / f"{stem}.png"
            if f.exists():
                emit(f, PUB / "finishes", slug, widths=[480, 960, 1600], upscale=True)
            else:
                print(f"  MISSING {folder}/{stem}.png")

    # ---- 2g. Engineering feature cards -----------------------------------
    # One photograph per claim in "Four things a lift is judged on". The sources
    # are 4:3, which is the frame's own ratio, so nothing is cropped.
    FEATURES = {
        "floor levelling within ...": "eng-precision",
        "no gear box": "eng-silence",
        "steel weges": "eng-safety",
        "everystart and stop is curve": "eng-performance",
    }
    fd = ROOT / "Zion Website" / "feature cards"
    print("engineering:")
    for stem, slug in FEATURES.items():
        f = fd / f"{stem}.png"
        if f.exists():
            emit(f, PUB / "engineering", slug, widths=[480, 960, 1600], upscale=True)
        else:
            print(f"  MISSING feature cards/{stem}.png")

    # ---- 2e. Certification marks ------------------------------------------
    # These are painted through a CSS mask in the accent colour, so all the file
    # has to carry is coverage in its alpha channel. Most of the source logos
    # are one solid ink on transparency, so their own alpha IS the shape. TUV
    # SUD is a filled octagon with a white centre and its alpha covers the whole
    # badge, so its shape has to be keyed off luminance or it masks to a blob.
    import numpy as np

    def _alpha(a):
        return a[..., 3] / 255

    def _ink(a, cut=0.78, soft=0.10):
        lum = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
        return np.clip((cut - lum) / soft, 0, 1) * (a[..., 3] / 255)

    CERTS = {
        "TUV_SUD": ("cert-tuv-sud", _ink),
        "CE": ("cert-ce", _alpha),
        "Iso": ("cert-iso", _alpha),
        "En": ("cert-en", _alpha),
        "ISI": ("cert-isi", _alpha),
    }
    cdir = ROOT / "Zion Website" / "Certifications"
    out = PUB / "certs"
    out.mkdir(parents=True, exist_ok=True)
    print("certs:")
    for stem, (slug, fn) in CERTS.items():
        f = cdir / f"{stem}.png"
        if not f.exists():
            continue
        a = np.asarray(Image.open(f).convert("RGBA"), dtype=np.float32)
        m = fn(a)
        ys, xs = np.nonzero(m > 0.06)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        rgba = np.zeros((*m.shape, 4), np.uint8)
        rgba[..., :3] = 255
        rgba[..., 3] = (m * 255).round()
        img = Image.fromarray(rgba, "RGBA")
        s = 360 / max(img.size)
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
        img.save(out / f"{slug}.png")
        print(f"  {slug}: {img.size}")

    # ---- 2d. The installation journey ------------------------------------
    # Four stages of one lift, in narrative order. The sources are ~1100px
    # portraits and lib/media.js promises a 1600 step for this bucket, so the
    # top size is upscaled rather than skipped — a missing width 404s and the
    # SPA fallback hands index.html to an <img>.
    JOURNEY = [
        ("Blueprint", "process-blueprint"),
        ("Structure", "process-structure"),
        ("Finished lift", "process-finished"),
        ("in the building", "process-building"),
    ]
    print("process:")
    for stem, slug in JOURNEY:
        f = ROOT / "Zion Website" / f"{stem}.png"
        if f.exists():
            emit(f, PUB / "process", slug, widths=[480, 960, 1600], upscale=True)

    # ---- 2c. Cabin specifications ----------------------------------------
    # One render per specification in the cabin section, keyed to the SPECS
    # slugs in pages/home/Cabin.jsx.
    specs = {
        "ceiling": "ceiling 1",
        "walls": "wall and",
        "flooring": "Flooring",
        "panel": "Control panel",
        "doors": "door and entrance",
    }
    sd = ROOT / "Zion Website" / "section 2"
    if sd.is_dir():
        print("cabin:")
        for slug, stem in specs.items():
            f = sd / f"{stem}.png"
            if f.exists():
                emit(f, PUB / "cabin", f"cabin-{slug}", widths=[480, 960, 1600])

    # ---- 3. Real project photo -------------------------------------------
    p = ROOT / "videos-20260828T181837Z-1-004" / "Zion pics-videos" / "16. Lekha Nilayam" / "Photos" / "AVP06751.jpg"
    if p.exists():
        print("projects:")
        emit(p, PUB / "projects", "lekha-nilayam-01")

    # ---- 4. Logos ---------------------------------------------------------
    ld = PUB / "brand"
    ld.mkdir(parents=True, exist_ok=True)
    for n, slug in ((1, "mark"), (2, "lockup"), (3, "alt")):
        f = ROOT / "logos" / f"{n}.png"
        if not f.exists():
            continue
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGBA")
        # trim the white field so the mark can sit on dark grounds
        bbox = im.convert("RGB").point(lambda v: 0 if v > 244 else 255).convert("L").getbbox()
        if bbox:
            im = im.crop(bbox)
        # white -> transparent
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if r > 238 and g > 238 and b > 238:
                    px[x, y] = (r, g, b, 0)
        im.save(ld / f"{slug}.png", "PNG", optimize=True)
        im.resize((round(im.width * 512 / im.height), 512) if im.height > 512 else im.size,
                  Image.LANCZOS).save(ld / f"{slug}.webp", "WEBP", quality=92)
        print(f"  brand/{slug}: {im.width}x{im.height}")

if __name__ == "__main__":
    main()
    print("ALL IMAGES DONE")
