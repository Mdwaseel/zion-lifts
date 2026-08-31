# -*- coding: utf-8 -*-
"""Cut the Zion logo out of its white field and emit light/dark variants.

The supplied PNGs carry a correct alpha channel but sit on an opaque white
canvas, so they are flattened onto white, trimmed to the ink, and given a fresh
alpha ramped off distance-from-white. The wordmark ships black (for pale
grounds) and warm-white (for the obsidian sections).
"""
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "media" / "brand"
WHITE = (243, 241, 236)


def cut(path):
    im = Image.open(path).convert("RGBA")
    flat = Image.alpha_composite(Image.new("RGBA", im.size, (255,) * 4), im).convert("RGB")
    rgb = np.asarray(flat).astype(np.int32)      # int32: the ramp below overflows int16
    ink = 255 - rgb.min(axis=2)
    ys, xs = np.where(ink > 18)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    alpha = np.clip((ink - 10) * 255 // 45, 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb.astype(np.uint8), alpha])
    return np.ascontiguousarray(rgba[y0:y1, x0:x1])


def to_light(arr):
    """Recolour the neutral black wordmark to warm white; leave the mark's teal alone."""
    out = arr.copy()
    rgb = out[..., :3].astype(np.int16)
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    neutral_dark = (mx < 120) & ((mx - mn) < 45)
    for i, v in enumerate(WHITE):
        out[..., i][neutral_dark] = v
    return out


def save(arr, slug, heights=(400, 96)):
    im = Image.fromarray(arr, "RGBA")
    im.save(OUT / f"{slug}.png", optimize=True)
    for h in heights:
        if h >= im.height:
            continue
        w = max(1, round(im.width * h / im.height))
        suffix = "" if h == heights[0] else f"-{h}"
        im.resize((w, h), Image.LANCZOS).save(
            OUT / f"{slug}{suffix}.webp", "WEBP", quality=95, method=6
        )
    opaque = int((arr[..., 3] > 200).sum())
    print(f"  {slug}: {im.width}x{im.height}  opaque={opaque:,}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("alt.*"):
        stale.unlink()

    mark = cut(ROOT / "logos" / "1.png")   # 1.png is the symbol on its own
    save(mark, "mark")
    save(to_light(mark), "mark-light")

    lock = cut(ROOT / "logos" / "2.png")
    save(lock, "lockup")
    save(to_light(lock), "lockup-light")


if __name__ == "__main__":
    main()
