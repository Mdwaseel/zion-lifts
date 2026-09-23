"""Turning a User-Agent header into three short words, and then forgetting it.

This is a deliberately small classifier rather than a dependency. A full UA
database exists to tell you that something is Chrome 118.0.5993.89 on Windows
11 — and the dashboard asks "Chrome or Safari?", "desktop or phone?". Carrying a
few megabytes of regexes and a monthly update obligation to answer a
five-bucket question is the wrong trade, and the narrower classifier has a
second virtue: it *cannot* accidentally start recording a fingerprint, because
there is nowhere for the detail to go.

The header itself is never stored. It is read on the way in, reduced to
(device, browser, os) here, and dropped when the request ends.

Order matters throughout. Every browser lies about being every other browser —
Edge says "Chrome" and "Safari", Chrome says "Safari" — so the checks run from
the most specific claim to the least, and the first match wins.
"""

from __future__ import annotations

from .models import Device

# Substrings that mean "this is not a person". Checked first: a crawler that
# says "Chrome" would otherwise land in the desktop/Chrome bucket and quietly
# inflate every number on the dashboard.
BOT_MARKERS = (
    "bot", "crawler", "spider", "slurp", "curl", "wget", "python-requests",
    "httpx", "headlesschrome", "phantomjs", "lighthouse", "pingdom", "uptime",
    "monitor", "scrapy", "facebookexternalhit", "embedly", "preview",
)

# (marker, name). Edge and Opera before Chrome; Chrome before Safari.
BROWSERS = (
    ("edg/", "Edge"),
    ("edga/", "Edge"),
    ("edgios/", "Edge"),
    ("opr/", "Opera"),
    ("opera", "Opera"),
    ("samsungbrowser", "Samsung Internet"),
    ("firefox/", "Firefox"),
    ("fxios/", "Firefox"),
    ("crios/", "Chrome"),
    ("chrome/", "Chrome"),
    ("chromium/", "Chrome"),
    ("safari/", "Safari"),
    ("msie", "Internet Explorer"),
    ("trident/", "Internet Explorer"),
)

# iOS before macOS: an iPhone's UA contains "like Mac OS X". Android before
# Linux, for the same reason in the other direction.
OPERATING_SYSTEMS = (
    ("windows phone", "Windows Phone"),
    ("windows", "Windows"),
    ("android", "Android"),
    ("iphone", "iOS"),
    ("ipad", "iOS"),
    ("ipod", "iOS"),
    ("cros", "ChromeOS"),
    ("mac os x", "macOS"),
    ("macintosh", "macOS"),
    ("linux", "Linux"),
)

TABLET_MARKERS = ("ipad", "tablet", "kindle", "silk", "playbook")
MOBILE_MARKERS = ("mobile", "iphone", "ipod", "android", "phone", "blackberry", "opera mini")


def classify(user_agent: str | None) -> tuple[str, str, str]:
    """``(device, browser, os)`` for a User-Agent header.

    Never raises and never returns an empty string: an unparseable or absent
    header is "unknown"/"Other"/"Other", which is a truthful row rather than a
    gap the dashboard has to special-case.
    """
    ua = (user_agent or "").lower()
    if not ua:
        return Device.UNKNOWN, "Other", "Other"

    if any(marker in ua for marker in BOT_MARKERS):
        return Device.BOT, "Bot", "Other"

    return _device(ua), _first_match(ua, BROWSERS), _first_match(ua, OPERATING_SYSTEMS)


def _device(ua: str) -> str:
    # Tablet first: an Android tablet's UA says "Android" and usually omits
    # "Mobile", but plenty of them include it, and a 10-inch screen is not a
    # phone whichever way the string reads.
    if any(marker in ua for marker in TABLET_MARKERS):
        return Device.TABLET
    if "android" in ua and "mobile" not in ua:
        return Device.TABLET
    if any(marker in ua for marker in MOBILE_MARKERS):
        return Device.MOBILE
    return Device.DESKTOP


def _first_match(ua: str, table: tuple[tuple[str, str], ...]) -> str:
    for marker, name in table:
        if marker in ua:
            return name
    return "Other"


def is_bot(user_agent: str | None) -> bool:
    """Whether this request should be counted at all.

    Exposed separately from :func:`classify` because the tracker uses it as a
    gate rather than as a label — bot traffic is not written, so it cannot skew
    a number later by being forgotten in a filter.
    """
    return any(marker in (user_agent or "").lower() for marker in BOT_MARKERS)
