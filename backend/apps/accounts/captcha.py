"""Text CAPTCHA for the login form.

The challenge is rendered server-side into a PNG and handed to the browser with
an opaque id. The *answer* never leaves the server: only a salted HMAC of it is
stored, in the cache, under that id.

Properties the login view relies on:

* short-lived — ``CAPTCHA_TTL_SECONDS`` (5 minutes by default);
* single-use — a correct answer deletes the entry, so a captured
  (captcha_id, answer) pair cannot be replayed;
* guess-limited — ``CAPTCHA_MAX_ATTEMPTS`` wrong answers burn the challenge,
  which is what stops a script from walking the alphabet against one image;
* case-insensitive — the glyphs are drawn rotated and warped, so demanding the
  right case would punish humans without troubling a solver.

Cache, not a table: these rows are worthless after five minutes and would
otherwise need a sweeper. The project already depends on the default cache for
DRF throttling, so this adds no new infrastructure. See the note on ``CACHES``
in ``zion/settings.py`` before running more than one worker.
"""

from __future__ import annotations

import base64
import io
import secrets
from dataclasses import dataclass
from typing import Final

from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import constant_time_compare, salted_hmac
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Ambiguity is the enemy of a text CAPTCHA: O/0, I/1/L and S/5 are guesses even
# for a patient human, so they are simply not in the alphabet.
ALPHABET: Final = "ABCDEFGHJKMNPQRTUVWXYZ23456789"

_KEY_PREFIX: Final = "accounts:captcha:"
_HMAC_SALT: Final = "apps.accounts.captcha"

_WIDTH: Final = 240
_HEIGHT: Final = 78

# Brand neutrals, so the challenge belongs to the page it sits on.
_BG: Final = (245, 244, 242)
_INK: Final = [(29, 29, 31), (4, 89, 90), (48, 48, 52), (6, 111, 112)]
_NOISE: Final = (150, 148, 143)


@dataclass(frozen=True)
class Challenge:
    """What the API hands to the browser. Deliberately holds no answer."""

    captcha_id: str
    image: str  # data:image/png;base64,...


def _key(captcha_id: str) -> str:
    return f"{_KEY_PREFIX}{captcha_id}"


def _attempts_key(captcha_id: str) -> str:
    """Wrong guesses live under their own key so they can be counted atomically."""
    return f"{_KEY_PREFIX}{captcha_id}:attempts"


def _digest(answer: str) -> str:
    """Salted HMAC of the normalised answer, keyed by SECRET_KEY.

    Storing the digest rather than the text means a cache dump (a Redis
    ``KEYS *``, a memory snapshot) does not hand over live challenges.
    """
    return salted_hmac(_HMAC_SALT, answer.strip().upper(), algorithm="sha256").hexdigest()


def _font(size: int):
    """A truetype face if the host has one, else Pillow's own scalable default."""
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _render(text: str) -> bytes:
    """Draw the characters individually, each rotated and offset off-baseline.

    A solver's easiest win is a fixed baseline and even spacing, which segments
    the image for it. Per-character rotation and jitter removes that, while
    staying comfortably readable at the 240px the login card gives it.
    """
    canvas = Image.new("RGB", (_WIDTH, _HEIGHT), _BG)
    draw = ImageDraw.Draw(canvas)

    for _ in range(420):  # speckle, so a flood fill cannot isolate the glyphs
        draw.point((secrets.randbelow(_WIDTH), secrets.randbelow(_HEIGHT)), fill=_NOISE)

    font = _font(42)
    step = (_WIDTH - 36) // max(len(text), 1)
    for index, char in enumerate(text):
        glyph = Image.new("RGBA", (60, 68), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text((8, 4), char, font=font, fill=(*secrets.choice(_INK), 255))
        glyph = glyph.rotate(secrets.randbelow(45) - 22, resample=Image.BICUBIC, expand=False)
        canvas.paste(glyph, (18 + index * step, 2 + secrets.randbelow(12)), glyph)

    # Strokes drawn last, over the text: a line that only crosses the
    # background is trivial to subtract.
    for _ in range(3):
        points = [(secrets.randbelow(_WIDTH), secrets.randbelow(_HEIGHT)) for _ in range(3)]
        draw.line(points, fill=secrets.choice(_INK), width=2, joint="curve")

    canvas = canvas.filter(ImageFilter.SMOOTH)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def issue_challenge() -> Challenge:
    """Create a challenge, store its digest, and return the public half."""
    # secrets, not random: the answer is the thing an attacker wants to predict,
    # and random's Mersenne Twister is reconstructable from its own output.
    answer = "".join(secrets.choice(ALPHABET) for _ in range(settings.CAPTCHA_LENGTH))
    captcha_id = secrets.token_urlsafe(18)

    cache.set(_key(captcha_id), _digest(answer), timeout=settings.CAPTCHA_TTL_SECONDS)

    image = base64.b64encode(_render(answer)).decode("ascii")
    return Challenge(captcha_id=captcha_id, image=f"data:image/png;base64,{image}")


def verify_challenge(captcha_id: str, answer: str) -> bool:
    """Check an answer, consuming the challenge on success or on exhaustion.

    Returns False for unknown, expired, exhausted and simply wrong answers
    alike — the caller cannot tell them apart, and neither can the client.
    """
    if not captcha_id or not answer:
        return False

    digest = cache.get(_key(captcha_id))
    if not digest:
        return False

    if constant_time_compare(digest, _digest(answer)):
        # Single use has to be decided by one atomic operation, not by a
        # read-then-delete: N requests carrying the same solved pair would all
        # pass the comparison above before any of them removed the entry, which
        # would turn one solved CAPTCHA into N password guesses. `delete`
        # reports whether it was the caller that actually removed the key, so
        # exactly one of those N wins.
        if not cache.delete(_key(captcha_id)):
            return False
        cache.delete(_attempts_key(captcha_id))
        return True

    if _count_attempt(captcha_id) >= settings.CAPTCHA_MAX_ATTEMPTS:
        invalidate(captcha_id)
    return False


def invalidate(captcha_id: str) -> None:
    cache.delete(_key(captcha_id))
    cache.delete(_attempts_key(captcha_id))


def _count_attempt(captcha_id: str) -> int:
    """Increment the wrong-guess counter atomically and return the new total.

    `incr` is atomic on both the locked LocMemCache and Redis; a get/modify/set
    would lose updates under concurrency and the guess limit would never bind.
    The counter carries its own TTL, set once when it is created, so a wrong
    answer can never extend the challenge's own window.
    """
    key = _attempts_key(captcha_id)
    try:
        return cache.incr(key)
    except ValueError:  # first wrong guess for this challenge
        if cache.add(key, 1, timeout=settings.CAPTCHA_TTL_SECONDS):
            return 1
        # Another request created it in between; count against the same key.
        try:
            return cache.incr(key)
        except ValueError:
            return 1
