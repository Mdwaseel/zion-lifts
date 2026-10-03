"""Cabin-configurator plates for the finishes that have no render of their own.

Each new option is built from the nearest existing render (frontend/public/
media/finishes), so it shares that render's lighting, lens and colour:

  material-gold          the antique-brass cabin, toned to polished gold
  control-tft            the brushed-steel COP with a large TFT screen let in
  control-full-touch     the glass COP redrawn as one touch screen
  floor-wooden           the marble floor relaid in wood, in perspective
  floor-tiles            the same floor relaid in vitrified tiles
  door-swing             the collapsible-gate landing refitted with a swing door
  door-half-glass        the same landing with a half-glazed swing door
  door-plain-ss          the centre-opening landing with plain steel leaves
  light-wall-lamps       the downlit ceiling, its light moved to wall lamps
  light-chandelier       the cove ceiling with a crystal chandelier

They are stand-ins until purpose-made renders arrive: drop a render at the
same name and re-run build_images.py, and it replaces the composite.

  python make_plates.py                 # all plates
  python make_plates.py tft gold        # just these
  python make_plates.py --preview DIR   # write previews to DIR as well
"""

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage
from skimage.transform import ProjectiveTransform, warp

ROOT = Path(__file__).resolve().parents[2]
FIN = ROOT / "frontend" / "public" / "media" / "finishes"
MEDIA = ROOT / "frontend" / "public" / "media"
FONTS = Path("C:/Windows/Fonts")
WIDTHS = [480, 960, 1600]

PREVIEW = None


# --- io ----------------------------------------------------------------------


def load(name):
    """an existing plate as float RGB in 0..1"""
    return np.asarray(Image.open(FIN / f"{name}.jpg").convert("RGB")).astype(np.float32) / 255


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def save(arr, slug):
    """the plate at 1600 wide as JPEG, plus the WebP widths the site's srcset asks for"""
    im = to_img(arr)
    if im.width != 1600:
        im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
    im.save(FIN / f"{slug}.jpg", quality=86, optimize=True, progressive=True)
    for w in WIDTHS:
        im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(
            FIN / f"{slug}-{w}.webp", quality=82, method=4
        )
    if PREVIEW:
        im.resize((640, round(im.height * 640 / im.width)), Image.LANCZOS).save(
            Path(PREVIEW) / f"{slug}.jpg", quality=88
        )
    print("  wrote", slug, im.size)


def font(name, px):
    return ImageFont.truetype(str(FONTS / name), int(px))


# --- geometry ---------------------------------------------------------------


def homography(src_pts, dst_pts):
    t = ProjectiveTransform()
    t.estimate(np.array(src_pts, dtype=np.float64), np.array(dst_pts, dtype=np.float64))
    return t


def paste_warped(base, rgba, dst_quad):
    """lay a flat RGBA image onto `base` so its corners land on `dst_quad`
    (TL, TR, BR, BL in image pixels)"""
    h, w = rgba.shape[:2]
    t = homography([(0, 0), (w, 0), (w, h), (0, h)], dst_quad)
    out = warp(rgba, t.inverse, output_shape=base.shape[:2], order=1, mode="constant", cval=0)
    a = out[..., 3:4]
    return base * (1 - a) + out[..., :3] * a


def quad_point(quad, u, v):
    """a point at fractions (u, v) across a quad's local rectangle"""
    t = homography([(0, 0), (1, 0), (1, 1), (0, 1)], quad)
    return tuple(t(np.array([[u, v]]))[0])


def sub_quad(quad, u0, v0, u1, v1):
    return [quad_point(quad, u0, v0), quad_point(quad, u1, v0), quad_point(quad, u1, v1), quad_point(quad, u0, v1)]


def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m


def rgba(im, mask=None):
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
    if mask is not None:
        a[..., 3] *= np.asarray(mask).astype(np.float32) / 255
    return a


def vgradient(w, h, top, bottom):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.array(top, np.float32) / 255 * (1 - t) + np.array(bottom, np.float32) / 255 * t
    return Image.fromarray((np.repeat(g, w, axis=1) * 255).astype(np.uint8))


def glow(layer, radius, strength=1.0):
    """a soft bloom around the bright parts of an RGBA layer"""
    blur = layer.filter(ImageFilter.GaussianBlur(radius))
    out = Image.alpha_composite(Image.new("RGBA", layer.size, (0, 0, 0, 0)), blur)
    if strength != 1.0:
        a = np.asarray(out).astype(np.float32)
        a[..., 3] *= strength
        out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return Image.alpha_composite(out, layer)


TEAL = (46, 201, 202)
WHITE = (240, 244, 245)


def zion_mark(height, color=(240, 244, 245)):
    """the Zion triangle, recoloured, at a given height"""
    m = Image.open(MEDIA / "brand" / "mark-light.png").convert("RGBA")
    m = m.resize((round(m.width * height / m.height), height), Image.LANCZOS)
    a = m.getchannel("A")
    out = Image.new("RGBA", m.size, color + (0,))
    out.putalpha(a)
    return out


def arrow_up(d, cx, top, w, h, fill):
    d.polygon([(cx, top), (cx + w / 2, top + h * 0.5), (cx + w * 0.16, top + h * 0.5),
               (cx + w * 0.16, top + h), (cx - w * 0.16, top + h), (cx - w * 0.16, top + h * 0.5),
               (cx - w / 2, top + h * 0.5)], fill=fill)


# --- material: gold ---------------------------------------------------------


def plate_gold():
    src = load("material-antique-brass")
    L = 0.2126 * src[..., 0] + 0.7152 * src[..., 1] + 0.0722 * src[..., 2]
    lo, hi = np.percentile(L, 1), np.percentile(L, 99.5)
    t = np.clip((L - lo) / (hi - lo), 0, 1) ** 0.92
    # a gradient map: deep bronze shadow, rich gold, pale specular
    stops = np.array([[0.00, 42, 26, 6], [0.30, 118, 80, 22], [0.58, 196, 148, 52],
                      [0.80, 234, 196, 98], [1.00, 255, 240, 186]], dtype=np.float32)
    gold = np.stack([np.interp(t, stops[:, 0], stops[:, c + 1] / 255) for c in range(3)], -1)
    save(0.82 * gold + 0.18 * src, "material-gold")


# --- control: TFT screen COP --------------------------------------------------

# the brushed panel's face: TL, TR, BR, BL (it is turned a little, right side away)
COP_FACE = [(648, 140), (953, 228), (953, 1765), (648, 1825)]
COP_LOCAL = (300, 1640)  # the face's own proportions, near enough 1 px : 1 unit


def photo_tile(path, w, h, pos=(0.5, 0.5)):
    im = Image.open(path).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    x = int((im.width - w) * pos[0])
    y = int((im.height - h) * pos[1])
    return im.crop((x, y, x + w, y + h))


def tft_screen(w, h):
    """what a 15.5-inch TFT on a car operating panel shows: the floor, the way
    the car is going, the time, and a message the building chooses"""
    im = vgradient(w, h, (16, 26, 31), (5, 9, 12)).convert("RGBA")
    d = ImageDraw.Draw(im)
    pad = w * 0.075
    small = font("segoeuisl.ttf", w * 0.05)
    d.text((pad, pad * 0.85), "10:45", fill=(206, 216, 219), font=small)
    d.text((w - pad, pad * 0.85), "THU 03 OCT", fill=(150, 162, 166), font=small, anchor="ra")
    # brand
    mark = zion_mark(round(h * 0.055))
    im.alpha_composite(mark, (round(w / 2 - mark.width / 2), round(h * 0.085)))
    # the floor, large, with the direction of travel
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    big = font("segoeuil.ttf", h * 0.3)
    ld.text((w * 0.58, h * 0.305), "3", fill=WHITE + (255,), font=big, anchor="mm")
    arrow_up(ld, w * 0.25, h * 0.215, w * 0.17, h * 0.13, TEAL + (255,))
    im = Image.alpha_composite(im, glow(layer, w * 0.02, 0.7))
    d = ImageDraw.Draw(im)
    d.text((w / 2, h * 0.45), "GOING UP", fill=TEAL + (255,), font=font("segoeuib.ttf", w * 0.045),
           anchor="mm")
    # the building's own message: a photograph and a line
    tw, th = round(w - 2 * pad), round(h * 0.27)
    tile = photo_tile(MEDIA / "frames" / "lekha-hall.jpg", tw, th, (0.5, 0.45))
    im.paste(tile, (round(pad), round(h * 0.52)), rounded_mask(tw, th, round(w * 0.03)))
    d.text((pad, h * 0.825), "Welcome home", fill=(236, 240, 241), font=font("segoeuib.ttf", w * 0.062))
    d.text((pad, h * 0.872), "Lekha Nilayam  ·  Floor 3", fill=(150, 162, 166), font=small)
    # status line
    d.line([(pad, h * 0.925), (w - pad, h * 0.925)], fill=(60, 72, 78), width=max(1, round(w * 0.004)))
    tiny = font("segoeuisl.ttf", w * 0.044)
    d.text((pad, h * 0.955), "8 persons · 544 kg", fill=(132, 144, 148), font=tiny, anchor="lm")
    d.text((w - pad, h * 0.955), "24°C", fill=(132, 144, 148), font=tiny, anchor="rm")
    return im


def plate_tft():
    base = load("control-brushed-cop")
    W, H = COP_LOCAL
    # the screen in the panel's own units: under the top screws, over the old
    # logo, display, sign and speaker, clear of the first row of buttons
    u0, u1, v0, v1 = 24, 276, 56, 618
    quad = sub_quad(COP_FACE, u0 / W, v0 / H, u1 / W, v1 / H)
    sw, sh = (u1 - u0) * 4, (v1 - v0) * 4
    screen = tft_screen(sw, sh)
    # a thin black bezel, then glass: a soft sheen across the top left
    bez = round(sw * 0.022)
    framed = Image.new("RGBA", (sw, sh), (8, 9, 10, 255))
    framed.alpha_composite(screen.resize((sw - 2 * bez, sh - 2 * bez), Image.LANCZOS), (bez, bez))
    sheen = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(sheen).polygon([(0, 0), (sw * 0.75, 0), (0, sh * 0.42)], fill=26)
    sheen = sheen.filter(ImageFilter.GaussianBlur(sw * 0.06))
    framed = Image.composite(Image.new("RGBA", (sw, sh), (255, 255, 255, 255)), framed, sheen)
    layer = rgba(framed, rounded_mask(sw, sh, round(sw * 0.05)))
    out = paste_warped(base, layer, quad)
    # the screen sits proud of the steel: a faint shadow below and to the right
    shadow = np.zeros(base.shape[:2], np.float32)
    sq = np.array(sub_quad(COP_FACE, (u0 + 6) / W, (v0 + 8) / H, (u1 + 6) / W, (v1 + 10) / H))
    from skimage.draw import polygon as poly

    rr, cc = poly(sq[:, 1], sq[:, 0], shadow.shape)
    shadow[rr, cc] = 1
    shadow = ndimage.gaussian_filter(shadow, 7) * 0.35
    inside = np.zeros_like(shadow)
    q = np.array(quad)
    rr, cc = poly(q[:, 1], q[:, 0], inside.shape)
    inside[rr, cc] = 1
    shadow *= 1 - ndimage.gaussian_filter(inside, 1.2)
    out = out * (1 - shadow[..., None])
    save(out, "control-tft")


# --- control: full touch COP ----------------------------------------------------

# the glass face of the touch panel: TL, TR, BR, BL (right side nearer)
TOUCH_FACE = [(700, 282), (996, 241), (996, 1862), (699, 1812)]
TOUCH_LOCAL = (300, 1575)


def touch_screen(w, h):
    """one glass touch screen: the floor and time at the head, every floor as a
    key, the door, alarm and intercom keys below"""
    im = vgradient(w, h, (10, 14, 17), (3, 5, 7)).convert("RGBA")
    d = ImageDraw.Draw(im)
    u = w / 300  # one panel unit, in canvas pixels
    # head: brand, the floor, the time
    mark = zion_mark(round(26 * u))
    im.alpha_composite(mark, (round(w / 2 - mark.width / 2), round(38 * u)))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((w * 0.58, 150 * u), "4", fill=WHITE + (255,), font=font("segoeuil.ttf", 118 * u), anchor="mm")
    arrow_up(ld, w * 0.3, 112 * u, 46 * u, 62 * u, TEAL + (255,))
    im = Image.alpha_composite(im, glow(layer, 6 * u, 0.6))
    d = ImageDraw.Draw(im)
    d.text((w / 2, 232 * u), "10:45  ·  THU 03 OCT", fill=(140, 152, 156),
           font=font("segoeuisl.ttf", 13 * u), anchor="mm")
    d.line([(34 * u, 262 * u), (w - 34 * u, 262 * u)], fill=(48, 58, 63), width=max(1, round(1.2 * u)))

    # every floor as a key, two to a row
    keys = [["5", "6"], ["3", "4"], ["1", "2"], ["G", "B"]]
    kw, kh, gap = 104 * u, 104 * u, 18 * u
    x0 = (w - 2 * kw - gap) / 2
    y = 292 * u
    label = font("segoeuil.ttf", 46 * u)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for row in keys:
        for i, k in enumerate(row):
            x = x0 + i * (kw + gap)
            on = k == "4"
            box = [x, y, x + kw, y + kh]
            if on:
                ld.rounded_rectangle(box, radius=22 * u, fill=TEAL + (60,), outline=TEAL + (255,), width=round(2.4 * u))
                ld.text((x + kw / 2, y + kh / 2), k, fill=(220, 255, 255, 255), font=label, anchor="mm")
            else:
                ld.rounded_rectangle(box, radius=22 * u, fill=(255, 255, 255, 10), outline=(225, 232, 234, 110),
                                     width=round(1.6 * u))
                ld.text((x + kw / 2, y + kh / 2), k, fill=(232, 238, 240, 235), font=label, anchor="mm")
        y += kh + gap
    im = Image.alpha_composite(im, glow(layer, 5 * u, 0.55))
    d = ImageDraw.Draw(im)

    # door, alarm and intercom keys
    y += 14 * u
    d.line([(34 * u, y), (w - 34 * u, y)], fill=(48, 58, 63), width=max(1, round(1.2 * u)))
    y += 30 * u
    small = 48 * u
    cols = [x0 + kw / 2, x0 + kw + gap + kw / 2]

    def key_ring(cx, cy, color):
        d.ellipse([cx - small / 2 - 18 * u, cy - small / 2 - 18 * u, cx + small / 2 + 18 * u, cy + small / 2 + 18 * u],
                  outline=color + (150,), width=round(1.6 * u))

    # open: two triangles pointing apart; close: pointing together
    cy = y + 40 * u
    for cx, apart in zip(cols, (True, False)):
        key_ring(cx, cy, (225, 232, 234))
        s = 15 * u
        if apart:
            d.polygon([(cx - 4 * u, cy - s), (cx - 4 * u, cy + s), (cx - 4 * u - s, cy)], fill=WHITE)
            d.polygon([(cx + 4 * u, cy - s), (cx + 4 * u, cy + s), (cx + 4 * u + s, cy)], fill=WHITE)
        else:
            d.polygon([(cx - 4 * u - s, cy - s), (cx - 4 * u - s, cy + s), (cx - 4 * u, cy)], fill=WHITE)
            d.polygon([(cx + 4 * u + s, cy - s), (cx + 4 * u + s, cy + s), (cx + 4 * u, cy)], fill=WHITE)
    cy += 122 * u
    # alarm bell, amber
    amber = (244, 182, 66)
    cx = cols[0]
    key_ring(cx, cy, amber)
    d.chord([cx - 16 * u, cy - 20 * u, cx + 16 * u, cy + 26 * u], 180, 360, outline=amber, width=round(3 * u))
    d.line([(cx - 16 * u, cy + 3 * u), (cx - 19 * u, cy + 13 * u), (cx + 19 * u, cy + 13 * u), (cx + 16 * u, cy + 3 * u)],
           fill=amber, width=round(3 * u))
    d.ellipse([cx - 4 * u, cy + 15 * u, cx + 4 * u, cy + 22 * u], fill=amber)
    # intercom: a speaker grille
    cx = cols[1]
    key_ring(cx, cy, (225, 232, 234))
    for r in range(3):
        for c in range(3):
            d.ellipse([cx + (c - 1) * 11 * u - 3 * u, cy + (r - 1) * 11 * u - 3 * u,
                       cx + (c - 1) * 11 * u + 3 * u, cy + (r - 1) * 11 * u + 3 * u], fill=WHITE)
    # fan and light
    cy += 122 * u
    for cx, kind in zip(cols, ("fan", "light")):
        key_ring(cx, cy, (225, 232, 234))
        if kind == "fan":
            for k in range(3):
                a = math.radians(90 + k * 120)
                bx, by = cx + math.cos(a) * 10 * u, cy - math.sin(a) * 10 * u
                d.ellipse([bx - 8 * u, by - 8 * u, bx + 8 * u, by + 8 * u], outline=WHITE, width=round(2.4 * u))
            d.ellipse([cx - 3 * u, cy - 3 * u, cx + 3 * u, cy + 3 * u], fill=WHITE)
        else:
            d.ellipse([cx - 11 * u, cy - 18 * u, cx + 11 * u, cy + 6 * u], outline=WHITE, width=round(2.4 * u))
            d.line([(cx - 6 * u, cy + 12 * u), (cx + 6 * u, cy + 12 * u)], fill=WHITE, width=round(2.4 * u))
            d.line([(cx - 4 * u, cy + 18 * u), (cx + 4 * u, cy + 18 * u)], fill=WHITE, width=round(2.4 * u))
    # the emergency key, the one red thing on the glass
    red = (232, 72, 64)
    ey = cy + 112 * u
    d.rounded_rectangle([x0, ey - 30 * u, x0 + 2 * kw + gap, ey + 30 * u], radius=30 * u, outline=red,
                        width=round(2.4 * u))
    d.text((w / 2, ey), "EMERGENCY", fill=red, font=font("segoeuib.ttf", 17 * u), anchor="mm")
    # foot
    d.text((w / 2, h - 40 * u), "TOUCH TO SELECT", fill=(110, 122, 126), font=font("segoeuisl.ttf", 12 * u),
           anchor="mm")
    return im


def plate_full_touch():
    base = load("control-touch-cop")
    W, H = TOUCH_LOCAL
    sw, sh = W * 4, H * 4
    screen = touch_screen(sw, sh)
    # glass: a soft sheen top left, and the rounded corners of the panel
    sheen = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(sheen).polygon([(0, 0), (sw, 0), (0, sh * 0.3)], fill=20)
    sheen = sheen.filter(ImageFilter.GaussianBlur(sw * 0.08))
    screen = Image.composite(Image.new("RGBA", (sw, sh), (255, 255, 255, 255)), screen, sheen)
    inset = 7  # panel units kept for the metal rim
    quad = sub_quad(TOUCH_FACE, inset / W, inset / H, (W - inset) / W, (H - inset) / H)
    layer = rgba(screen, rounded_mask(sw, sh, round(sw * 0.09)))
    save(paste_warped(base, layer, quad), "control-full-touch")


# --- floors: relaid in perspective ------------------------------------------------

FLOOR_BASE = "floor-marble"


def _robust_line(xs, ys):
    """y = m x + b, refitted without the points that jumped to another edge"""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    keep = np.ones(len(xs), bool)
    for _ in range(3):
        m, b = np.polyfit(xs[keep], ys[keep], 1)
        res = np.abs(ys - (m * xs + b))
        keep = res < max(2.5, np.median(res[keep]) * 2.5)
    return m, b


def _meet(l1, l2):
    """intersection of y = m1 x + b1 and y = m2 x + b2"""
    (m1, b1), (m2, b2) = l1, l2
    x = (b2 - b1) / (m1 - m2)
    return x, m1 * x + b1


def _rays_meet(p, q, r, s):
    """intersection of the line through p, q with the line through r, s"""
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p, q, r, s
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    a = x1 * y2 - y1 * x2
    b = x3 * y4 - y3 * x4
    return ((a * (x3 - x4) - (x1 - x2) * b) / den, (a * (y3 - y4) - (y1 - y2) * b) / den)


def floor_geometry(img):
    """the floor's outline and the plane it lies in, read off the render: the
    two skirtings, the right jamb, and the left jamb and sill"""
    H, W = img.shape[:2]
    L = ndimage.gaussian_filter(img @ np.array([0.2126, 0.7152, 0.0722], np.float32), 1.0)
    ref = ndimage.median_filter(L, size=31)

    def scan(x, y, dx, dy, n=160, frac=0.78):
        # walk out from the floor until it is no longer floor
        r = ref[int(y), int(x)]
        for _ in range(n):
            xi, yi = int(round(x)), int(round(y))
            if not (0 <= xi < W - 2 and 0 <= yi < H - 2):
                break
            if L[yi, xi] < frac * r and L[yi + 2 * dy, xi + 2 * dx] < frac * r:
                break
            x, y = x + dx, y + dy
        return x, y

    left = [scan(x, -0.4629 * x + 1029.9 + 45, 0, -1) for x in range(215, 815, 5)]
    back = [scan(x, 0.2414 * x + 452.9 + 60, 0, -1) for x in range(835, 1505, 5)]
    jamb = [scan(-0.0466 * y + 1557.4 - 70, y, 1, 0) for y in range(840, H - 2, 5)]
    lowl = [scan(260 if y < 1150 else 260 + (y - 1150) * 0.85, y, -1, 0, n=200) for y in range(930, H - 2, 5)]

    l_left = _robust_line(*zip(*left))
    l_back = _robust_line(*zip(*back))
    # near-vertical edges are fitted as x = m y + b
    mj, bj = _robust_line(*zip(*[(y, x) for x, y in jamb]))
    mlj, blj = _robust_line(*zip(*[(y, x) for x, y in lowl if y < 1100]))
    l_sill = _robust_line(*zip(*[(x, y) for x, y in lowl if y > 1175]))

    def on_vertical(m, b, y):
        return (m * y + b, y)

    F = _meet(l_left, l_back)
    R = _rays_meet(F, (F[0] + 1, F[1] + l_back[0]), on_vertical(mj, bj, 0), on_vertical(mj, bj, H))
    BR = on_vertical(mj, bj, H + 40)
    BL = ((H + 40 - l_sill[1]) / l_sill[0], H + 40)
    SJ = _rays_meet(on_vertical(mlj, blj, 0), on_vertical(mlj, blj, H), (0, l_sill[1]), (1, l_sill[0] + l_sill[1]))
    LJ = _rays_meet(on_vertical(mlj, blj, 0), on_vertical(mlj, blj, H), (0, l_left[1]), (1, l_left[0] + l_left[1]))
    outline = [F, R, BR, BL, SJ, LJ]

    # the plane: lines across the cabin (back skirting, sill) meet at one
    # vanishing point; the horizon through it is level, and the left skirting,
    # which runs the cabin's depth, meets that horizon at the other
    vp_w = _meet(l_back, l_sill)
    vp_d = ((vp_w[1] - l_left[1]) / l_left[0], vp_w[1])
    N = _rays_meet(R, vp_d, LJ, vp_w)
    # floor units: u across the cabin (F to R), v along it (F to the front wall)
    plane = homography([(0, 0), (1, 0), (1, 1), (0, 1)], [F, R, N, LJ])
    return outline, plane


def polygon_mask(shape, pts, feather=1.2):
    m = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(m).polygon([(float(x), float(y)) for x, y in pts], fill=255)
    a = np.asarray(m).astype(np.float32) / 255
    return ndimage.gaussian_filter(a, feather) if feather else a


def relay_floor(texture, scale, slug, gloss=0.55, tone=1.0):
    """lay `texture` (RGB, `scale` px per millimetre) on the base floor, in its
    perspective and under its light"""
    base = load(FLOOR_BASE)
    H, W = base.shape[:2]
    outline, plane = floor_geometry(base)
    mask = polygon_mask(base.shape, outline)

    # where every pixel of the floor is, in the floor's own units
    yy, xx = np.mgrid[0:H, 0:W]
    uv = plane.inverse(np.stack([xx.ravel(), yy.ravel()], 1).astype(np.float64))
    # the cabin taken as 1,150 x 1,400 mm, the texture starting a little behind the corner
    mm_u = (uv[:, 0] * 1150 + 60) * scale
    mm_v = (uv[:, 1] * 1400 + 60) * scale
    coords = np.stack([mm_v.reshape(H, W), mm_u.reshape(H, W)])
    lay = np.stack(
        [ndimage.map_coordinates(texture[..., c], coords, order=1, mode="reflect") for c in range(3)], -1
    )

    # the light already on the marble, its veining blurred away: the broad
    # falloff, the darker corners, and the glossy streak
    Lb = base @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    inside = mask > 0.5
    shade = ndimage.gaussian_filter(Lb * mask, 22) / np.maximum(ndimage.gaussian_filter(mask, 22), 1e-3)
    shade = shade / np.median(shade[inside])
    # the colour of the light: what the marble shows, over what marble is
    light = np.median(base[inside], axis=0) / np.array([0.86, 0.83, 0.78], np.float32)
    lit = lay * light * (shade[..., None] ** 0.95) * tone
    spec = np.clip(shade - 1.08, 0, None)
    lit = lit + gloss * spec[..., None] * np.array([1.0, 0.96, 0.9], np.float32)
    # a contact shadow where the floor meets the skirting
    edge = ndimage.gaussian_filter(1 - polygon_mask(base.shape, outline, feather=0), 6)
    lit = lit * (1 - 0.45 * np.clip(edge, 0, 1)[..., None])
    out = base * (1 - mask[..., None]) + lit * mask[..., None]
    save(out, slug)


def _streaks(shape, along, across, rng):
    """fibrous noise, long in one direction"""
    n = rng.standard_normal(shape).astype(np.float32)
    n = ndimage.gaussian_filter(n, (along, across))
    return (n - n.mean()) / (n.std() + 1e-6)


def wood_texture(scale=1.5, seed=7):
    """engineered oak planks, 150 mm wide, running the depth of the cabin"""
    rng = np.random.default_rng(seed)
    h, w = int(1800 * scale), int(1600 * scale)  # rows run along v, columns across u
    tex = np.zeros((h, w, 3), np.float32)
    tones = np.array([[132, 94, 62], [120, 84, 54], [146, 104, 68], [112, 78, 50], [138, 98, 64]], np.float32) / 255
    grain = 0.6 * _streaks((h, w), 140 * scale, 1.1 * scale, rng) + 0.4 * _streaks(
        (h, w), 40 * scale, 0.6 * scale, rng
    )
    grain = np.tanh(grain * 1.4)  # crisper lines in the grain
    rings = _streaks((h, w), 260 * scale, 4 * scale, rng)
    pw = 150 * scale
    joint = np.zeros((h, w), np.float32)
    for c in range(int(w / pw) + 1):
        x0, x1 = int(c * pw), min(w, int((c + 1) * pw))
        y = -rng.uniform(0, 1200) * scale
        while y < h:
            ln = rng.uniform(900, 1500) * scale
            y0, y1 = max(0, int(y)), min(h, int(y + ln))
            if y1 > y0:
                tex[y0:y1, x0:x1] = tones[rng.integers(len(tones))] * rng.uniform(0.92, 1.08)
                joint[y0 : min(h, y0 + max(1, int(1.6 * scale))), x0:x1] = 1  # butt joint
            y += ln
        joint[:, x0 : min(w, x0 + max(1, int(1.8 * scale)))] = 1  # long edge
    tex *= (1 + 0.09 * grain + 0.08 * np.tanh(rings * 1.5))[..., None]
    # joints: a fine dark line with a lit bevel beside it
    j = ndimage.gaussian_filter(joint, 0.6 * scale)
    tex = tex * (1 - 0.55 * j[..., None])
    bevel = ndimage.shift(j, (0, 1.5 * scale), order=1) - j
    tex = tex + 0.05 * np.clip(bevel, 0, 1)[..., None]
    return np.clip(tex, 0, 1)


def tile_texture(scale=1.5, seed=3):
    """vitrified tiles, 600 x 600 mm, in a warm ivory with fine grout"""
    rng = np.random.default_rng(seed)
    h, w = int(1800 * scale), int(1600 * scale)
    tex = np.ones((h, w, 3), np.float32) * (np.array([226, 216, 200], np.float32) / 255)
    cloud = _streaks((h, w), 40 * scale, 40 * scale, rng)
    fine = _streaks((h, w), 2.2 * scale, 2.2 * scale, rng)
    t = 600 * scale
    grout = np.zeros((h, w), np.float32)
    off_u, off_v = 230 * scale, 170 * scale
    for r in range(-1, int(h / t) + 2):
        for c in range(-1, int(w / t) + 2):
            y0, x0 = int(r * t + off_v), int(c * t + off_u)
            ys = slice(max(0, y0), max(0, min(h, int(y0 + t))))
            xs = slice(max(0, x0), max(0, min(w, int(x0 + t))))
            tex[ys, xs] *= rng.uniform(0.985, 1.015)
            if 0 <= y0 < h:
                grout[y0 : min(h, y0 + int(2.5 * scale)), :] = 1
            if 0 <= x0 < w:
                grout[:, x0 : min(w, x0 + int(2.5 * scale))] = 1
    tex *= (1 + 0.012 * cloud + 0.01 * fine)[..., None]
    g = ndimage.gaussian_filter(grout, 0.7 * scale)[..., None]
    tex = tex * (1 - g) + (np.array([150, 140, 128], np.float32) / 255)[None, None] * g
    return np.clip(tex, 0, 1)


def plate_wooden():
    relay_floor(wood_texture(), 1.5, "floor-wooden", gloss=0.4, tone=1.05)


def plate_tiles():
    relay_floor(tile_texture(), 1.5, "floor-tiles", gloss=0.7)


# --- doors: new leaves in existing openings ----------------------------------------


def _soft_rect(h, w, x0, y0, x1, y1, blur=0.8):
    m = np.zeros((h, w), np.float32)
    m[int(round(y0)) : int(round(y1)), int(round(x0)) : int(round(x1))] = 1
    return ndimage.gaussian_filter(m, blur) if blur else m


def steel_leaf(profile_l, profile_r, w, rng, tone=0.94, grain=0.035):
    """brushed steel lit like the steel beside it: each row takes its light
    from the jambs either side, the grain runs vertically"""
    h = profile_l.shape[0]
    t = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    col = profile_l[:, None, :] * (1 - t) + profile_r[:, None, :] * t
    streak = 0.65 * _streaks((h, w), 120, 0.8, rng) + 0.35 * _streaks((h, w), 24, 0.5, rng)
    return np.clip(col * tone * (1 + grain * streak)[..., None], 0, 1)


def cabin_glass(h, w, warm=(1.0, 0.97, 0.93)):
    """what a vision panel shows: a dim cabin, its ceiling light, and the bright
    lobby reflected in the glass"""
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    # the lit cabin: a bright ceiling at the head of the glass, its light
    # falling down a pale back wall
    ceiling = 0.75 * np.clip(1 - yy / 0.07, 0, 1)
    spill = 0.24 + 0.22 * np.exp(-((xx - 0.5) ** 2) / 0.12 - (yy - 0.05) ** 2 / 0.09)
    falloff = 1 - 0.35 * yy
    interior = (np.maximum(spill * falloff, ceiling))[..., None] * np.array(warm, np.float32)
    # the back wall's panel joints, faint
    seams = np.zeros((h, w), np.float32)
    for f in (0.33, 0.67):
        seams[:, int(w * f) : int(w * f) + 2] = 1
    interior = interior * (1 - 0.25 * ndimage.gaussian_filter(seams, 0.8)[..., None])
    refl = np.clip(1 - np.abs((xx * 0.55 + yy * 0.45) - 0.32) / 0.13, 0, 1) * 0.16
    refl += np.clip(1 - np.abs((xx * 0.55 + yy * 0.45) - 0.55) / 0.05, 0, 1) * 0.07
    return np.clip(interior + refl[..., None] * np.array([0.92, 0.94, 0.97], np.float32), 0, 1)


def _pull_handle(leaf, cx, top, bottom, width, rng):
    """a round stainless pull: a cylinder lit from the left, its shadow on the leaf"""
    h, w = leaf.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    bar = ((np.abs(xx - cx) <= width / 2) & (yy >= top) & (yy <= bottom)).astype(np.float32)
    # standoffs
    for y in (top + width * 1.2, bottom - width * 1.2):
        bar = np.maximum(bar, ((np.abs(xx - cx) <= width * 0.42) & (np.abs(yy - y) <= width * 0.42)).astype(np.float32))
    shadow = ndimage.gaussian_filter(ndimage.shift(bar, (width * 0.5, width * 0.9), order=1), width * 0.6)
    leaf = leaf * (1 - 0.35 * shadow[..., None])
    across = np.clip((xx - (cx - width / 2)) / width, 0, 1)
    shade = 0.62 + 0.42 * np.sin(np.pi * np.clip(across * 0.85 + 0.08, 0, 1)) ** 1.6
    metal = np.stack([shade * 0.86, shade * 0.87, shade * 0.88], -1)
    a = ndimage.gaussian_filter(bar, 0.7)[..., None]
    return leaf * (1 - a) + metal * a


def swing_leaf(base, box, glass, rng):
    """a hinged steel leaf for the opening `box`; `glass` is (u0, v0, u1, v1) or None"""
    x0, y0, x1, y1 = box
    h, w = y1 - y0, x1 - x0
    # light from the steel jambs either side of the opening
    pl = ndimage.gaussian_filter1d(base[y0:y1, x0 - 30 : x0 - 10].mean(axis=1), 6, axis=0)
    pr = ndimage.gaussian_filter1d(base[y0:y1, x1 + 12 : x1 + 32].mean(axis=1), 6, axis=0)
    leaf = steel_leaf(pl, pr, w, rng, tone=0.9)
    if glass:
        u0, v0, u1, v1 = glass
        gx0, gy0, gx1, gy1 = u0 * w, v0 * h, u1 * w, v1 * h
        pane = cabin_glass(int(gy1 - gy0), int(gx1 - gx0))
        g = _soft_rect(h, w, gx0, gy0, gx1, gy1, 0.7)[..., None]
        canvas = np.zeros_like(leaf)
        canvas[int(gy0) : int(gy0) + pane.shape[0], int(gx0) : int(gx0) + pane.shape[1]] = pane
        leaf = leaf * (1 - g) + canvas * g
        # a steel bead round the glass: a lit edge outside, a dark line inside
        ring_out = _soft_rect(h, w, gx0 - 7, gy0 - 7, gx1 + 7, gy1 + 7, 0.8) - g[..., 0]
        ring_in = g[..., 0] - _soft_rect(h, w, gx0 + 2, gy0 + 2, gx1 - 2, gy1 - 2, 0.6)
        leaf = leaf * (1 + 0.1 * np.clip(ring_out, 0, 1))[..., None]
        leaf = leaf * (1 - 0.55 * np.clip(ring_in, 0, 1))[..., None]
    # the handle on the lock side, at hand height
    leaf = _pull_handle(leaf, w * 0.075, h * 0.43, h * 0.6, max(9, w * 0.016), rng)
    # the gap round the leaf, and the shade the transom throws on its head
    edge = 1 - _soft_rect(h, w, 3, 3, w - 3, h - 2, 1.1)
    leaf = leaf * (1 - 0.6 * edge)[..., None]
    head = np.clip(1 - np.arange(h, dtype=np.float32) / 40, 0, 1)[:, None]
    leaf = leaf * (1 - 0.12 * head)[..., None]
    out = base.copy()
    out[y0:y1, x0:x1] = leaf
    return out


SWING_OPENING = (545, 503, 1172, 1765)  # x0, y0, x1, y1 in door-manual-swing


def plate_door_swing():
    rng = np.random.default_rng(11)
    out = swing_leaf(load("door-manual-swing"), SWING_OPENING, (0.44, 0.15, 0.56, 0.62), rng)
    save(out, "door-swing")


def plate_door_half_glass():
    rng = np.random.default_rng(12)
    out = swing_leaf(load("door-manual-swing"), SWING_OPENING, (0.14, 0.07, 0.86, 0.47), rng)
    save(out, "door-half-glass")


def plate_door_plain():
    """the centre-opening landing with its glass taken out: two plain steel
    leaves, the kind that can carry a fire rating"""
    base = load("door-centre-auto")
    rng = np.random.default_rng(13)
    out = base.copy()
    y0, y1 = 652, 1594
    for x0, x1 in ((619, 800), (803, 984)):
        h, w = y1 - y0, x1 - x0
        # each leaf's own light, read off its outer stiles
        pl = ndimage.gaussian_filter1d(base[y0:y1, x0 + 3 : x0 + 15].mean(axis=1), 8, axis=0)
        pr = ndimage.gaussian_filter1d(base[y0:y1, x1 - 15 : x1 - 3].mean(axis=1), 8, axis=0)
        leaf = steel_leaf(pl, pr, w, rng, tone=1.0, grain=0.06)
        # a touch darker toward the meeting edge, where the two leaves close
        t = np.linspace(0, 1, w, dtype=np.float32)
        meet = t if x0 < 801 else 1 - t
        leaf = leaf * (1 - 0.06 * meet ** 3)[None, :, None]
        edge = 1 - _soft_rect(h, w, 2, 2, w - 2, h - 2, 0.9)
        leaf = leaf * (1 - 0.5 * edge)[..., None]
        out[y0:y1, x0:x1] = leaf
    save(out, "door-plain-ss")


# --- lighting: a chandelier, and wall lamps ---------------------------------------------

SRC = Path(__file__).resolve().parent / "src"
WARM = np.array([1.0, 0.82, 0.58], np.float32)  # the colour of the cabins' warm light


def gradient_map(t, stops):
    stops = np.asarray(stops, np.float32)
    return np.stack([np.interp(t, stops[:, 0], stops[:, c + 1] / 255) for c in range(3)], -1)


def plate_chandelier():
    """the cove ceiling with a tiered crystal chandelier hung at its centre,
    where the ceiling panels meet — a flush fitting that suits an 8-foot cabin"""
    from skimage.morphology import convex_hull_image

    base = load("light-cove")
    H, W = base.shape[:2]
    ph = np.asarray(Image.open(SRC / "chandelier-pexels-14772933.jpg").convert("RGB")).astype(np.float32) / 255
    L = ndimage.gaussian_filter(ph @ np.array([0.2126, 0.7152, 0.0722], np.float32), 1.0)

    # the matte: the chandelier's outline is the hull of its lit crystals; inside
    # it, the crystals by their own light, the dark background keyed out
    # the lit crystals, joined up; only the biggest group is the chandelier —
    # the small lights scattered behind it in the photograph are not
    lit = ndimage.binary_dilation(L > 0.3, iterations=14)
    lab, n = ndimage.label(lit)
    sizes = ndimage.sum(lit, lab, range(1, n + 1))
    hull = convex_hull_image((lab == 1 + int(np.argmax(sizes))) & (L > 0.3))
    hull = ndimage.binary_dilation(hull, iterations=10).astype(np.float32)
    ys, xs = np.nonzero(hull)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    hull = ndimage.gaussian_filter(hull, 4)[y0:y1, x0:x1]
    key = np.clip((L[y0:y1, x0:x1] - 0.05) / 0.11, 0, 1) ** 0.9
    alpha = hull * key

    # the photograph is lit red; recoloured to the cabin's warm gold
    # crystal in a lit room is bright: the mid-tones lifted to gold
    t = np.clip(L[y0:y1, x0:x1] / 0.48, 0, 1) ** 0.72
    fg = gradient_map(t, [[0.0, 26, 16, 8], [0.25, 120, 76, 34], [0.55, 222, 168, 98],
                          [0.8, 255, 228, 180], [1.0, 255, 250, 238]])

    # scaled to about half the ceiling's width and hung from the seam crossing
    target_w = 640
    s = target_w / (x1 - x0)
    nh, nw = int((y1 - y0) * s), target_w

    def rs(a):
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
        return np.asarray(im.resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255

    fg = np.stack([rs(fg[..., c]) for c in range(3)], -1)
    alpha, hull = rs(alpha), rs(hull)
    top, left = 585, 805 - nw // 2

    out = base.copy()
    # a broad warm lift on the ceiling around it, then the chandelier itself
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = np.exp(-(((xx - 805) / 340) ** 2) - ((yy - 760) / 300) ** 2)
    out = out * (1 + 0.32 * g[..., None] * WARM) + 0.05 * g[..., None] * WARM
    region = out[top : top + nh, left : left + nw]
    # the body of crystal veils the ceiling a little, then the crystals light up
    region = region * (1 - 0.12 * hull[..., None] * (1 - alpha[..., None]))
    region = region * (1 - alpha[..., None]) + fg * alpha[..., None]
    out[top : top + nh, left : left + nw] = region
    # bloom: the sparkle bleeding into the air round it
    lit = np.zeros_like(out)
    lit[top : top + nh, left : left + nw] = fg * alpha[..., None] * (fg.mean(-1, keepdims=True) > 0.55)
    bloom = np.stack([ndimage.gaussian_filter(lit[..., c], 5) * 0.55 + ndimage.gaussian_filter(lit[..., c], 28) * 0.45
                      for c in range(3)], -1)
    out = 1 - (1 - out) * (1 - bloom)  # screen
    save(out, "light-chandelier")


def sconce(canvas_h, canvas_w, rng):
    """a brass wall sconce with a glowing ivory drum shade, as RGBA, drawn at
    four times size: the shade, its rims, the brass back plate and the opening
    seen from just below"""
    k = 4
    w, h = canvas_w * k, canvas_h * k
    cx = w / 2
    sw, sh = 0.62 * w, 0.5 * h  # the shade
    sx0, sy0 = cx - sw / 2, 0.3 * h
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # brass back plate, above and below the shade
    pw = 0.14 * w
    d.rounded_rectangle([cx - pw / 2, 0.06 * h, cx + pw / 2, 0.94 * h], radius=pw * 0.45, fill=(120, 86, 42, 255))
    d.rounded_rectangle([cx - pw * 0.36, 0.08 * h, cx + pw * 0.05, 0.92 * h], radius=pw * 0.3, fill=(184, 142, 80, 255))
    d.rounded_rectangle([cx - pw * 0.28, 0.1 * h, cx - pw * 0.12, 0.9 * h], radius=pw * 0.1, fill=(236, 200, 136, 255))
    # the arm out to the shade
    d.rectangle([cx - pw * 0.18, 0.2 * h, cx + pw * 0.18, sy0 + 2 * k], fill=(176, 136, 76, 255))
    # the shade: lit fabric, brightest a little below centre where the lamp sits
    ys = np.linspace(0, 1, int(sh), dtype=np.float32)[:, None]
    xs = np.linspace(-1, 1, int(sw), dtype=np.float32)[None, :]
    # brightest in a band a little below centre, where the lamp sits; darker
    # toward the rims, and toward the sides where the drum turns away
    lum = 0.7 + 0.42 * np.exp(-((ys - 0.56) / 0.36) ** 2)
    lum = lum * (0.8 + 0.2 * np.clip(np.cos(np.clip(np.abs(xs), 0, 1) * np.pi / 2), 0, 1) ** 0.6)
    pleats = 1 + 0.03 * np.sin(xs * np.pi * 22) * (1 - 0.6 * np.abs(xs))
    weave = 1 + 0.02 * _streaks((int(sh), int(sw)), 18 * k, 0.6 * k, rng)
    col = np.array([255, 214, 158], np.float32) / 255
    shade = np.clip(lum[..., None] * (pleats * weave)[..., None] * col, 0, 1)
    shade_im = Image.fromarray((shade * 255).astype(np.uint8)).convert("RGBA")
    layer.alpha_composite(shade_im, (int(sx0), int(sy0)))
    # the brass rings top and bottom
    d = ImageDraw.Draw(layer)
    d.rectangle([sx0, sy0, sx0 + sw, sy0 + 2.2 * k], fill=(168, 128, 70, 255))
    d.rectangle([sx0, sy0 + sh - 2.4 * k, sx0 + sw, sy0 + sh], fill=(168, 128, 70, 255))
    # seen from a little below: the open bottom, bright
    d.ellipse([sx0 + 1.5 * k, sy0 + sh - 6 * k, sx0 + sw - 1.5 * k, sy0 + sh + 5 * k], fill=(255, 246, 226, 255))
    d.rectangle([sx0, sy0 + sh - 2.4 * k, sx0 + sw, sy0 + sh - 0.4 * k], fill=(168, 128, 70, 255))
    layer = layer.resize((canvas_w, canvas_h), Image.LANCZOS)
    return np.asarray(layer).astype(np.float32) / 255, (cx / k, sy0 / k, sw / k, sh / k)


def wall_wash(H, W, cx, top, bottom, width, up_len, down_len):
    """the light a drum shade throws on the wall: a cone up from its top
    opening, a shorter one down from its bottom, and a glow round the fabric"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = xx - cx
    # upward cone, opening as it rises; edges soft
    d_up = np.clip(top - yy, 0, None)
    half_up = width * 0.5 + d_up * 0.55
    up = np.exp(-((dx / half_up) ** 6)) * (1 / (1 + d_up / (up_len * 0.45)) ** 2) * (yy <= top)
    d_dn = np.clip(yy - bottom, 0, None)
    half_dn = width * 0.5 + d_dn * 0.4
    dn = np.exp(-((dx / half_dn) ** 6)) * (1 / (1 + d_dn / (down_len * 0.45)) ** 2) * (yy >= bottom)
    mid = (top + bottom) / 2
    halo = np.exp(-((dx / (width * 1.6)) ** 2) - ((yy - mid) / ((bottom - top) * 1.4)) ** 2)
    wash = 0.95 * up + 0.6 * dn + 0.55 * halo
    return ndimage.gaussian_filter(wash, 3)


def plate_wall_lamps():
    """the walnut cabin with a pair of brass wall lamps on its facing wall, the
    room dimmed so the lamps carry the light"""
    base = load("material-walnut")
    H, W = base.shape[:2]
    rng = np.random.default_rng(21)
    out = base * 0.74  # evening: the lamps are now the light
    lamps = []
    for cx in (178, 580):  # the centre of each of the facing wall's two panels
        cw, ch = 200, 300
        top = 330
        rgba_, (scx, sy0, sw, sh) = sconce(ch, cw, rng)
        shade_top, shade_bot = top + sy0, top + sy0 + sh
        lamps.append((cx, cw, ch, top, rgba_))
        wash = wall_wash(H, W, cx, shade_top, shade_bot, sw, 520, 330)
        # light adds to the wall in its own colour: the walnut's grain survives
        out = out + base * wash[..., None] * WARM * 2.6
    for cx, cw, ch, top, rgba_ in lamps:
        x0 = int(cx - cw / 2)
        region = out[top : top + ch, x0 : x0 + cw]
        a = rgba_[..., 3:4]
        out[top : top + ch, x0 : x0 + cw] = region * (1 - a) + rgba_[..., :3] * a
    # bloom round the shades
    glowing = np.zeros(out.shape[:2], np.float32)
    for cx, cw, ch, top, rgba_ in lamps:
        x0 = int(cx - cw / 2)
        glowing[top : top + ch, x0 : x0 + cw] = np.maximum(
            glowing[top : top + ch, x0 : x0 + cw], rgba_[..., 3] * np.clip((rgba_[..., :3].mean(-1) - 0.55) / 0.3, 0, 1)
        )
    bloom = ndimage.gaussian_filter(glowing, 8) * 0.45 + ndimage.gaussian_filter(glowing, 36) * 0.5
    out = 1 - (1 - out) * (1 - bloom[..., None] * WARM)
    save(np.clip(out, 0, 1), "light-wall-lamps")


PLATES = {
    "gold": plate_gold,
    "tft": plate_tft,
    "touch": plate_full_touch,
    "wooden": plate_wooden,
    "tiles": plate_tiles,
    "swing": plate_door_swing,
    "halfglass": plate_door_half_glass,
    "plain": plate_door_plain,
    "chandelier": plate_chandelier,
    "walllamps": plate_wall_lamps,
}

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--preview" in args:
        i = args.index("--preview")
        PREVIEW = args[i + 1]
        Path(PREVIEW).mkdir(parents=True, exist_ok=True)
        del args[i : i + 2]
    for name in args or PLATES:
        print(name)
        PLATES[name]()
