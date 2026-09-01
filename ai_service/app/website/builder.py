"""Turn the website's own content API into a page index.

The alternative was to write the site's copy out by hand in this service, and
that fails the moment somebody publishes a lift: the assistant would go on
describing a catalogue that no longer matches the one a visitor is looking at,
and there would be no signal that it had drifted. So the catalogue half of the
index is *fetched* — from the same read-only endpoints the React app calls, over
the same published-only querysets — and only the fixed pages (their names, their
sections, the words a visitor searches for) are declared statically, in
:mod:`app.website.routes`, because those change with a redesign rather than with
an edit.

Two rules shape everything below.

*A failure produces less, never nothing wrong.* If the backend is down, the
build falls back to the static pages alone: the assistant can still say the
products page exists and link to it, and simply cannot name individual models.
That is the correct degradation for a navigational index — a missing suggestion
costs a click, an invented URL costs trust.

*Nothing fetched is trusted as text.* Field values become searchable content and
page summaries, and they may end up quoted to a visitor, so they are length-
capped and stripped of markup here rather than at the point of use.
"""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.logging import get_logger
from app.website.index import WebsiteIndex
from app.website.models import PageKind, WebsitePage, WebsiteSection
from app.website.routes import STATIC_PAGES

logger = get_logger(__name__)

# Long enough to describe a product, short enough that a page summary cannot
# become the whole prompt.
_MAX_SUMMARY = 600
_MAX_SECTION = 900

_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")

# The collections worth indexing, and nothing else. Finishes, gallery items and
# team members are content on pages already in the static list; adding them
# would add terms without adding a destination.
_ENDPOINTS = ("lifts", "projects", "journal", "offices", "site")


def clean(value: object, limit: int = _MAX_SUMMARY) -> str:
    """A field from the API as plain, bounded text."""
    if not isinstance(value, str) or not value:
        return ""
    text = _SPACES.sub(" ", html.unescape(_TAGS.sub(" ", value))).strip()
    return text[:limit].rstrip() if len(text) > limit else text


@dataclass(slots=True)
class SiteContent:
    """The raw payloads, one per endpoint. Absent keys mean that call failed."""

    lifts: list[dict[str, Any]]
    projects: list[dict[str, Any]]
    journal: list[dict[str, Any]]
    offices: list[dict[str, Any]]
    site: dict[str, Any]
    partial: bool = False


async def fetch_content(
    base_url: str, client: httpx.AsyncClient, timeout: float = 10.0
) -> SiteContent:
    """Read the public content API. Never raises; a failed call yields nothing.

    Each endpoint is fetched independently and a failure is confined to its own
    collection, because the failure modes are independent: a serializer error on
    one collection should not cost the index every other one.
    """
    payloads: dict[str, Any] = {name: [] for name in _ENDPOINTS}
    payloads["site"] = {}
    partial = False
    root = base_url.rstrip("/")

    for name in _ENDPOINTS:
        try:
            response = await client.get(f"{root}/api/{name}/", timeout=timeout)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            partial = True
            logger.warning(
                "website content fetch failed",
                extra={"collection": name, "error_type": type(exc).__name__},
            )
            continue

        if name == "site":
            payloads[name] = body if isinstance(body, dict) else {}
        elif isinstance(body, list):
            payloads[name] = body
        elif isinstance(body, dict) and isinstance(body.get("results"), list):
            # Tolerated rather than expected: these endpoints set
            # pagination_class = None, but a future default would silently
            # halve the index if this branch were missing.
            payloads[name] = body["results"]
        else:
            partial = True

    return SiteContent(
        lifts=payloads["lifts"],
        projects=payloads["projects"],
        journal=payloads["journal"],
        offices=payloads["offices"],
        site=payloads["site"],
        partial=partial,
    )


def _lift_page(record: dict[str, Any]) -> WebsitePage | None:
    slug = record.get("slug")
    if not isinstance(slug, str) or not slug:
        return None

    name = clean(record.get("name"), 120) or slug.replace("-", " ").title()
    applications = [
        clean(a.get("name"), 60)
        for a in record.get("applications", [])
        if isinstance(a, dict) and a.get("name")
    ]

    # The numbers a visitor asks a product question with. Assembled as a
    # sentence rather than a dict so it reads correctly if it is ever quoted.
    specs = [
        f"{label} {clean(record.get(key), 80)}"
        for key, label in (
            ("capacity", "Capacity:"),
            ("speed", "Speed:"),
            ("stops", "Stops:"),
            ("drive", "Drive:"),
            ("machine_room", "Machine room:"),
        )
        if clean(record.get(key), 80)
    ]

    sections = [
        WebsiteSection("Overview", clean(record.get("summary"), _MAX_SECTION)),
    ]
    if specs:
        sections.append(WebsiteSection("Specifications", "; ".join(specs)))
    if applications:
        sections.append(WebsiteSection("Applications", ", ".join(applications)))

    return WebsitePage(
        route=f"/lifts/{slug}",
        title=name,
        kind=PageKind.PRODUCT,
        summary=clean(record.get("tagline"), 200) or clean(record.get("summary"), 200),
        description=clean(record.get("summary")),
        keywords=tuple(
            k
            for k in (
                name.lower(),
                slug.replace("-", " "),
                clean(record.get("short_name"), 60).lower(),
                clean(record.get("eyebrow"), 60).lower(),
                *(a.lower() for a in applications),
                "lift",
                "elevator",
            )
            if k
        ),
        sections=tuple(s for s in sections if s.text),
        product_slugs=(slug,),
    )


def _project_page(record: dict[str, Any]) -> WebsitePage | None:
    slug = record.get("slug")
    if not isinstance(slug, str) or not slug:
        return None
    name = clean(record.get("name"), 160) or slug.replace("-", " ").title()
    category = record.get("category")
    category_name = clean(category.get("name"), 60) if isinstance(category, dict) else ""

    return WebsitePage(
        route=f"/projects/{slug}",
        title=name,
        kind=PageKind.PROJECT,
        summary=clean(record.get("statement"), 200) or clean(record.get("summary"), 200),
        description=clean(record.get("summary")),
        keywords=tuple(
            k
            for k in (
                name.lower(),
                clean(record.get("client"), 120).lower(),
                clean(record.get("location"), 120).lower(),
                category_name.lower(),
                "project",
                "installation",
                "case study",
            )
            if k
        ),
        sections=tuple(
            s
            for s in (
                WebsiteSection("Challenge", clean(record.get("challenge"), _MAX_SECTION)),
                WebsiteSection("Solution", clean(record.get("solution"), _MAX_SECTION)),
                WebsiteSection("Result", clean(record.get("result"), _MAX_SECTION)),
            )
            if s.text
        ),
    )


def _journal_page(record: dict[str, Any]) -> WebsitePage | None:
    slug = record.get("slug")
    if not isinstance(slug, str) or not slug:
        return None
    category = record.get("category")
    category_name = clean(category.get("name"), 60) if isinstance(category, dict) else ""

    return WebsitePage(
        route=f"/journal/{slug}",
        title=clean(record.get("title"), 200) or slug.replace("-", " ").title(),
        kind=PageKind.JOURNAL,
        summary=clean(record.get("excerpt"), 300),
        description=clean(record.get("excerpt")),
        keywords=tuple(
            k for k in (slug.replace("-", " "), category_name.lower(), "article", "journal") if k
        ),
    )


def _contact_page(offices: list[dict[str, Any]], site: dict[str, Any]) -> WebsitePage | None:
    """The static contact page, enriched with the offices that actually exist.

    Locality names are what make "where is your Hyderabad office?" reach this
    page rather than a project that happens to be in Hyderabad, so they are
    folded into its keywords. The addresses themselves become section text,
    which is what lets the answer name one instead of describing the page.
    """
    base = next((p for p in STATIC_PAGES if p.route == "/contact"), None)
    if base is None or not offices:
        return None

    sections = list(base.sections)
    keywords = list(base.keywords)
    for office in offices[:6]:
        if not isinstance(office, dict):
            continue
        label = clean(office.get("name"), 120) or clean(office.get("city"), 80)
        parts = [
            clean(office.get("address"), 300),
            clean(office.get("city"), 80),
            clean(office.get("phone"), 40),
            clean(office.get("email"), 120),
            clean(office.get("hours"), 160),
        ]
        body = ", ".join(p for p in parts if p)
        if label and body:
            sections.append(WebsiteSection(label, body))
        for term in (office.get("city"), office.get("locality"), office.get("state")):
            value = clean(term, 80).lower()
            if value:
                keywords.append(value)

    for key in ("phone", "email", "city"):
        value = clean(site.get(key), 120).lower()
        if value:
            keywords.append(value)

    return WebsitePage(
        route=base.route,
        title=base.title,
        kind=base.kind,
        summary=base.summary,
        description=base.description,
        keywords=tuple(dict.fromkeys(keywords)),
        sections=tuple(sections),
    )


def build_pages(content: SiteContent | None) -> list[WebsitePage]:
    """The static pages, plus one page per published record.

    A record that produces no route — no slug — is skipped rather than given a
    generated one. The index's guarantee is that every route in it is real, and
    a route derived from a record that did not name itself is not.
    """
    pages: list[WebsitePage] = []
    contact_override: WebsitePage | None = None

    if content is not None:
        contact_override = _contact_page(content.offices, content.site)
        for record, factory in (
            *((r, _lift_page) for r in content.lifts),
            *((r, _project_page) for r in content.projects),
            *((r, _journal_page) for r in content.journal),
        ):
            if not isinstance(record, dict):
                continue
            page = factory(record)
            if page is not None:
                pages.append(page)

    static = [
        contact_override if contact_override and page.route == "/contact" else page
        for page in STATIC_PAGES
    ]

    # Product slugs are folded into the products index so that naming a model
    # can reach the catalogue as well as the model's own page.
    lift_slugs = tuple(p.route.rsplit("/", 1)[-1] for p in pages if p.kind is PageKind.PRODUCT)
    lift_names = tuple(p.title.lower() for p in pages if p.kind is PageKind.PRODUCT)
    static = [
        WebsitePage(
            route=page.route,
            title=page.title,
            kind=page.kind,
            summary=page.summary,
            description=page.description,
            keywords=page.keywords + lift_names,
            sections=page.sections,
            product_slugs=lift_slugs,
        )
        if page.route == "/lifts"
        else page
        for page in static
    ]

    return static + pages


async def build_index(
    base_url: str | None, client: httpx.AsyncClient | None = None, timeout: float = 10.0
) -> WebsiteIndex:
    """Build the live index, or the static one when there is no backend.

    ``base_url`` unset is a legitimate configuration — a development machine
    running the AI service alone — and produces the static index rather than an
    error. The assistant is then navigationally correct and catalogue-blind,
    which is exactly what it should be when it cannot see the catalogue.
    """
    if not base_url:
        logger.info("website index built from static routes only", extra={"reason": "no_backend"})
        return WebsiteIndex(build_pages(None), generated_at=time.time())

    owns_client = client is None
    client = client or httpx.AsyncClient(follow_redirects=True)
    try:
        content = await fetch_content(base_url, client, timeout)
    finally:
        if owns_client:
            await client.aclose()

    index = WebsiteIndex(build_pages(content), generated_at=time.time())
    logger.info(
        "website index built",
        extra={
            "pages": len(index),
            "lifts": len(content.lifts),
            "projects": len(content.projects),
            "articles": len(content.journal),
            "partial": content.partial,
        },
    )
    return index


__all__ = ["SiteContent", "build_index", "build_pages", "clean", "fetch_content"]
