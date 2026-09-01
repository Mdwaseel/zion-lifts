"""Where a visit came from, reduced to a host and one of five channels.

The full referring URL is never stored. A referrer carries the search someone
typed, or the path of the private document that linked here, and neither is
ours — so the URL is parsed on the way in, the host is kept, and the rest is
discarded before anything is written.

Classification is a fixed table rather than a configurable one on purpose. The
five channels are the ones a decision gets made about ("should we keep paying
for search?"), and a taxonomy that grows a bucket per referring domain stops
answering that question.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from .models import Channel

SEARCH_HOSTS = (
    "google.", "bing.", "duckduckgo.", "yahoo.", "yandex.", "baidu.",
    "ecosia.", "brave.com", "startpage.", "search.", "qwant.", "ask.com",
)

SOCIAL_HOSTS = (
    "facebook.", "fb.com", "instagram.", "linkedin.", "lnkd.in", "twitter.",
    "x.com", "t.co", "pinterest.", "reddit.", "youtube.", "youtu.be",
    "whatsapp.", "wa.me", "telegram.", "t.me", "tiktok.", "threads.",
    "quora.", "tumblr.", "snapchat.",
)


def referrer_host(referrer: str | None) -> str:
    """The bare host of a referring URL, lowercased and without ``www.``.

    Returns "" for anything unparseable, which is the same answer as "no
    referrer" and is treated identically downstream — a malformed header is not
    worth a distinct code path.
    """
    if not referrer:
        return ""
    try:
        host = urlsplit(referrer.strip()).netloc.lower()
    except ValueError:
        return ""
    host = host.split("@")[-1].split(":")[0]  # strip credentials and port
    if host.startswith("www."):
        host = host[4:]
    return host[:160]


def classify(referrer: str | None, own_hosts: tuple[str, ...] = ()) -> tuple[str, str]:
    """``(channel, referrer_host)`` for a referring URL.

    ``own_hosts`` are this site's own domains. A referrer pointing at one of
    them is an internal link, which is not a traffic source at all — counting it
    as a referral would make the site its own biggest promoter, which is both
    useless and the most common way this table gets read wrong.
    """
    host = referrer_host(referrer)
    if not host:
        return Channel.DIRECT, ""

    if any(host == own or host.endswith(f".{own}") for own in own_hosts if own):
        return Channel.DIRECT, ""

    if any(marker in host for marker in SEARCH_HOSTS):
        return Channel.SEARCH, host
    if any(marker in host for marker in SOCIAL_HOSTS):
        return Channel.SOCIAL, host
    return Channel.REFERRAL, host
