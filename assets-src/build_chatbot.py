# -*- coding: utf-8 -*-
"""Emit the assistant's mascot at the sizes the launcher actually uses.

The master is a ~1.1 MB PNG at well over a thousand pixels square. The launcher
draws it at 26px and the panel header at 30px, so shipping the master would send
a megabyte to every visitor on first paint to fill a space the size of a
fingernail — and the assistant is mounted on every page of the site.

The master already carries a clean alpha channel, so there is nothing to cut
out; this only trims the transparent margin (which is most of the canvas edge)
and resizes. WebP for the browsers that take it, one small PNG as the fallback.
"""
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "brand-src" / "chatbot.png"
OUT = ROOT / "frontend" / "public" / "media" / "chatbot"

# 2x and 3x of the two sizes it is drawn at, so a retina screen has a real
# pixel for every device pixel and nothing is upscaled.
WIDTHS = (64, 96, 128)
FALLBACK_WIDTH = 96

# Anything below this alpha is margin, not artwork.
ALPHA_FLOOR = 8


def trim(im: Image.Image) -> Image.Image:
    """Crop away the fully transparent border.

    ``getbbox`` on the alpha channel alone; the RGB channels carry colour in
    pixels that are invisible, so a bbox over the whole image would not trim.
    """
    box = im.getchannel("A").point(lambda a: 255 if a > ALPHA_FLOOR else 0).getbbox()
    return im.crop(box) if box else im


def main():
    if not SRC.exists():
        raise FileNotFoundError(f"Missing the chatbot master at {SRC}")

    OUT.mkdir(parents=True, exist_ok=True)
    master = trim(Image.open(SRC).convert("RGBA"))

    for width in WIDTHS:
        height = max(1, round(master.height * width / master.width))
        resized = master.resize((width, height), Image.LANCZOS)
        resized.save(OUT / f"chatbot-{width}.webp", "WEBP", quality=90, method=6)
        if width == FALLBACK_WIDTH:
            resized.save(OUT / "chatbot.png", optimize=True)

    largest = OUT / f"chatbot-{WIDTHS[-1]}.webp"
    print(
        f"  chatbot: master {master.width}x{master.height}"
        f" -> {', '.join(str(w) for w in WIDTHS)}px"
        f"  ({largest.stat().st_size / 1024:.1f} kB at {WIDTHS[-1]}px)"
    )


if __name__ == "__main__":
    main()
