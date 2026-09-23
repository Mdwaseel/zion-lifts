"""Where a visitor was, if the infrastructure already knows and nothing else.

There is no IP geolocation here, and that is the design rather than a gap.
Resolving a location means either shipping a MaxMind database and its update
obligation, or sending every visitor's address to a third party — and both start
by handling the one value this app has otherwise been careful never to touch.

So the rule is: geography is recorded **only if a proxy in front of Django has
already resolved it** and passed the answer down as a header. A CDN doing the
lookup at the edge has the IP anyway; taking its conclusion adds no exposure.
Behind a plain gunicorn with no such proxy, these columns stay empty and the
dashboard says "no location data" rather than inventing one.

``ANALYTICS_GEO_HEADERS`` lets a deployment name its own headers. The defaults
cover Cloudflare, Vercel, Fastly and Google Cloud's load balancer.

**Trust.** Headers are client-supplied unless something strips them, so this is
only safe when a proxy you control overwrites them on the way in — the same
assumption ``NUM_PROXIES`` already makes for throttling. A deployment with no
such proxy should leave ``ANALYTICS_GEO_HEADERS`` empty; the cost of a wrong
setting here is a wrong country on a chart, not a leak.
"""

from __future__ import annotations

from django.conf import settings

# (field, header) in priority order — the first header present wins.
DEFAULT_HEADERS = {
    "country": (
        "HTTP_CF_IPCOUNTRY",           # Cloudflare
        "HTTP_X_VERCEL_IP_COUNTRY",    # Vercel
        "HTTP_X_COUNTRY_CODE",         # Fastly, and common nginx/GeoIP setups
        "HTTP_X_APPENGINE_COUNTRY",    # Google Cloud
    ),
    "region": (
        "HTTP_CF_REGION",
        "HTTP_X_VERCEL_IP_COUNTRY_REGION",
        "HTTP_X_APPENGINE_REGION",
    ),
    "city": (
        "HTTP_CF_IPCITY",
        "HTTP_X_VERCEL_IP_CITY",
        "HTTP_X_APPENGINE_CITY",
    ),
}

# ISO codes for the places this site actually sells into, expanded so the table
# reads as names. Anything else is shown as its code, which is still useful and
# does not require carrying a 250-row country list for a decoration.
COUNTRY_NAMES = {
    "IN": "India", "US": "United States", "GB": "United Kingdom", "AE": "United Arab Emirates",
    "SA": "Saudi Arabia", "QA": "Qatar", "OM": "Oman", "KW": "Kuwait", "BH": "Bahrain",
    "SG": "Singapore", "MY": "Malaysia", "AU": "Australia", "CA": "Canada", "DE": "Germany",
    "FR": "France", "NL": "Netherlands", "IT": "Italy", "ES": "Spain", "JP": "Japan",
    "CN": "China", "LK": "Sri Lanka", "BD": "Bangladesh", "NP": "Nepal", "PK": "Pakistan",
    "ZA": "South Africa", "NG": "Nigeria", "KE": "Kenya", "BR": "Brazil", "IE": "Ireland",
    "NZ": "New Zealand", "CH": "Switzerland", "SE": "Sweden", "NO": "Norway", "PL": "Poland",
}


def resolve(request) -> dict[str, str]:
    """``{"country", "region", "city"}`` from trusted proxy headers.

    Every value is empty when no proxy supplied one. Nothing here reads
    ``REMOTE_ADDR`` or any forwarded-for header — the address is not consulted
    even to be thrown away.
    """
    headers = getattr(settings, "ANALYTICS_GEO_HEADERS", DEFAULT_HEADERS)
    meta = request.META
    out = {}
    for field, candidates in headers.items():
        value = ""
        for header in candidates:
            raw = (meta.get(header) or "").strip()
            # Cloudflare sends "XX" for addresses it could not place, and "T1"
            # for Tor. Both are absence dressed up as an answer.
            if raw and raw.upper() not in {"XX", "T1", "UNKNOWN"}:
                value = raw
                break
        out[field] = _clean(field, value)
    return out


def _clean(field: str, value: str) -> str:
    if not value:
        return ""
    if field == "country":
        code = value.upper()[:2]
        return COUNTRY_NAMES.get(code, code)
    return value[:64]
