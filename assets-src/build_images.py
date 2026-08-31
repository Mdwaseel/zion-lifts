# -*- coding: utf-8 -*-
"""Optimise Zion source imagery into responsive webp/jpg sets for the React app."""
import pathlib
from PIL import Image, ImageOps

ROOT = pathlib.Path(r"d:\Projects\Zion Lifts")
PUB  = ROOT / "frontend" / "public" / "media"

WIDTHS = [480, 960, 1600, 2400]

def emit(src: pathlib.Path, out_dir: pathlib.Path, slug: str, widths=WIDTHS, cover=None):
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
        if w > im.width * 1.05:
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
    files = sorted(src.glob("*.png"), key=lambda p: int("".join(c for c in p.stem if c.isdigit()) or 0))
    print("interiors:")
    for i, f in enumerate(files, 1):
        emit(f, PUB / "interiors", f"interior-{i:02d}")

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
