# -*- coding: utf-8 -*-
"""Pull hand-picked stills from the 4K project masters.

Zion's films contain the photography the site otherwise has no source for:
real cabins, real control panels, real drive hardware, real people using the
lifts. Timestamps below were chosen by reviewing contact sheets of each film.
`crop_bottom` trims the burnt-in caption band where one is present.
"""
import io
import pathlib
import subprocess

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "videos-20260828T181837Z-1-004"
OUT = ROOT / "frontend" / "public" / "media" / "frames"
WIDTHS = [480, 960, 1600]

MASTERS = {
    "lacheta": "Lacheta Nivas V F Video 1",
    "kashi": "Kasi Yadav V F Video",
    "chath": "Chath H Video O1",
    "lekha": "Lekha Nilayam H F Video",
    "niloufer": "Testimonal-1_Niloufer F",
    "chilkuru": "Chilukuru F House Final video",
    "owaisi": "Owaisi hospital Final Video",
}

# (film, seconds, slug, crop_bottom_fraction)
SHOTS = [
    # --- Lacheta Nivas: brass + marble private residence --------------------
    ("lacheta",   3.0, "lacheta-exterior",   0.10),
    ("lacheta",   8.8, "lacheta-ceiling",    0.0),
    ("lacheta",  14.7, "lacheta-indicator",  0.0),
    ("lacheta",  17.6, "lacheta-lobby",      0.0),
    ("lacheta",  23.5, "lacheta-cop",        0.0),
    ("lacheta",  26.4, "lacheta-inuse",      0.0),
    ("lacheta",  32.2, "lacheta-stair",      0.0),
    ("lacheta",  35.2, "lacheta-glass",      0.0),
    ("lacheta",  38.1, "lacheta-terrace",    0.0),

    # --- Kashi Yadhav: glass shaft + exposed drive hardware -----------------
    ("kashi",     3.0, "kashi-exterior",     0.10),
    ("kashi",     9.3, "kashi-cabin",        0.0),
    ("kashi",    12.5, "kashi-interior",     0.0),
    ("kashi",    18.8, "kashi-floor",        0.0),
    ("kashi",    21.9, "kashi-lop",          0.0),
    ("kashi",    25.1, "kashi-shaft",        0.0),
    ("kashi",    28.2, "kashi-stair",        0.0),
    ("kashi",    37.7, "kashi-drive",        0.0),
    ("kashi",    40.8, "kashi-machine",      0.0),
    ("kashi",    44.0, "kashi-structure",    0.0),

    # --- Chath: hospitality, wood-clad ---------------------------------------
    ("chath",     5.0, "chath-aerial",       0.12),
    ("chath",     7.3, "chath-facade",       0.0),
    ("chath",    11.6, "chath-entrance",     0.0),
    ("chath",    13.8, "chath-terrace",      0.0),
    ("chath",    15.9, "chath-inuse",        0.0),
    ("chath",    20.2, "chath-indicator",    0.0),
    ("chath",    24.5, "chath-cabin",        0.0),
    ("chath",    28.8, "chath-ceiling",      0.0),

    # --- Lekha Nilayam: drone exterior + panoramic home lift ----------------
    ("lekha",     3.0, "lekha-aerial",       0.0),
    ("lekha",     6.5, "lekha-exterior",     0.0),
    ("lekha",     9.9, "lekha-approach",     0.0),
    ("lekha",    13.4, "lekha-hall",         0.0),
    ("lekha",    16.8, "lekha-cabin",        0.0),
    ("lekha",    20.3, "lekha-cop",          0.0),
    ("lekha",    27.2, "lekha-ceiling",      0.0),
    ("lekha",    34.2, "lekha-inuse",        0.0),
    ("lekha",    41.1, "lekha-corridor",     0.0),

    # --- Owaisi Hospitals: institutional, banks of lifts --------------------
    ("owaisi",    8.2, "owaisi-exterior",    0.12),
    ("owaisi",   10.8, "owaisi-lobby",       0.12),
    ("owaisi",   13.5, "owaisi-doors",       0.12),
    ("owaisi",   16.1, "owaisi-cabin",       0.12),
    ("owaisi",   18.7, "owaisi-ceiling",     0.12),
    ("owaisi",   21.3, "owaisi-cop",         0.12),
    ("owaisi",   26.5, "owaisi-waiting",     0.12),
    ("owaisi",   31.8, "owaisi-corridor",    0.12),

    # --- Chilkuru Residence: villa + capsule lift in atrium -----------------
    ("chilkuru",  3.0, "chilkuru-aerial",    0.12),
    ("chilkuru",  6.2, "chilkuru-pavilion",  0.0),
    ("chilkuru", 12.7, "chilkuru-entrance",  0.0),
    ("chilkuru", 15.9, "chilkuru-corridor",  0.0),
    ("chilkuru", 19.2, "chilkuru-capsule",   0.12),
    ("chilkuru", 25.6, "chilkuru-ceiling",   0.0),
    ("chilkuru", 28.8, "chilkuru-panel",     0.0),
    ("chilkuru", 32.1, "chilkuru-atrium",    0.0),
    ("chilkuru", 38.5, "chilkuru-lop",       0.12),

    # --- Niloufer Cafe: client testimonial ----------------------------------
    ("niloufer",  4.0, "niloufer-portrait",  0.0),
    ("niloufer", 30.0, "niloufer-cabin",     0.0),
    ("niloufer", 60.0, "niloufer-interior",  0.0),
]


def master(key):
    frag = MASTERS[key].lower()
    for p in SRC.rglob("*"):
        if p.suffix.lower() == ".mov" and frag in p.name.lower():
            return p
    raise FileNotFoundError(MASTERS[key])


def grab(path, seconds):
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(seconds), "-i", str(path),
         "-vframes", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True,
    )
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(r.stderr.decode()[:200])
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cache = {}
    for key, secs, slug, crop_bottom in SHOTS:
        if key not in cache:
            cache[key] = master(key)
        try:
            im = grab(cache[key], secs)
        except Exception as e:
            print(f"  ! {slug}: {e}")
            continue
        if crop_bottom:
            im = im.crop((0, 0, im.width, int(im.height * (1 - crop_bottom))))
        made = []
        for w in WIDTHS:
            if w > im.width * 1.05:
                continue
            h = round(im.height * w / im.width)
            im.resize((w, h), Image.LANCZOS).save(
                OUT / f"{slug}-{w}.webp", "WEBP", quality=84, method=6
            )
            made.append(w)
        fw = made[-1] if made else im.width
        im.resize((fw, round(im.height * fw / im.width)), Image.LANCZOS).save(
            OUT / f"{slug}.jpg", "JPEG", quality=85, optimize=True, progressive=True
        )
        print(f"  + {slug}  {im.width}x{im.height} -> {made}")
    print(f"\n{len(SHOTS)} stills -> {OUT}")


if __name__ == "__main__":
    main()
