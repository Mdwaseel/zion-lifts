"""Paths into the React app's public asset tree, produced by `assets-src/*.py`.

Keeping them in one place means a renamed file breaks loudly at seed time
rather than silently rendering a hole on the page.
"""

BASE = "/media"


def interior(n):
    """One of the ten luxury installation photographs (portrait)."""
    return f"{BASE}/interiors/interior-{n:02d}.jpg"


def product(family, n):
    """Capsule / car-stacker / dumbwaiter renders (landscape)."""
    return f"{BASE}/products/{family}-{n:02d}.jpg"


def frame(slug):
    """A still harvested from one of the 4K project films."""
    return f"{BASE}/frames/{slug}.jpg"


def sourced(slug):
    """CC-licensed stand-in — see frontend/public/media/ATTRIBUTION.md."""
    return f"{BASE}/sourced/{slug}.jpg"


def video(slug, loop=False):
    return f"{BASE}/video/{slug}{'-loop' if loop else ''}.mp4"


def poster(slug):
    return f"{BASE}/poster/{slug}.jpg"


BRAND_MARK = f"{BASE}/brand/mark.png"
BRAND_LOCKUP = f"{BASE}/brand/lockup.png"
BRAND_LOCKUP_LIGHT = f"{BASE}/brand/lockup-light.png"
