"""The site's route table, and the only list of URLs the assistant may produce.

This mirrors the ``<Route>`` elements in ``frontend/src/App.jsx``. It is written
out rather than derived because the two live in different languages on different
sides of a network boundary, and a link the assistant offers must be checkable
without asking the browser — a suggestion that 404s is worse than no suggestion
at all.

Two consequences follow, and both are deliberate:

*Nothing outside this module may invent a route.* :func:`route_exists` is the
gate, and the index refuses to hold a page whose route does not pass it. A model
that writes ``/products/magic-lift`` produces no link rather than a broken one.

*Adding a page to the site means adding a line here.* That is the cost of the
guarantee. The alternative — trusting a generated URL — is how a chatbot ends up
confidently linking to a page that has never existed.

The static entries below also carry the page's own copy: the sections a visitor
sees, and the words they would use to look for them. That content is small,
changes at the pace of a redesign rather than of a data edit, and has to exist
even when the backend is unreachable — so it lives here, and everything that
*does* change per record (a lift, a project, a post) is fetched instead, in
:mod:`app.website.builder`.
"""

from __future__ import annotations

import re
from typing import Final

from app.website.models import PageKind, WebsitePage, WebsiteSection

# Route templates for the pages whose path carries a slug. A concrete URL is
# only valid if a record with that slug exists, which is why these are separate
# from the static list and why the index checks them against real slugs.
DYNAMIC_ROUTES: Final[tuple[tuple[str, PageKind], ...]] = (
    ("/lifts/{slug}", PageKind.PRODUCT),
    ("/projects/{slug}", PageKind.PROJECT),
    ("/journal/{slug}", PageKind.JOURNAL),
)

_DYNAMIC_MATCHERS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(rf"^{template.replace('{slug}', '[a-z0-9][a-z0-9-]*')}$")
    for template, _ in DYNAMIC_ROUTES
)


def _page(
    route: str,
    title: str,
    kind: PageKind,
    summary: str,
    keywords: tuple[str, ...],
    sections: tuple[tuple[str, str], ...] = (),
) -> WebsitePage:
    return WebsitePage(
        route=route,
        title=title,
        kind=kind,
        summary=summary,
        keywords=keywords,
        sections=tuple(WebsiteSection(name=name, text=text) for name, text in sections),
    )


# The fixed pages. Order is the order a person would meet them.
STATIC_PAGES: Final[tuple[WebsitePage, ...]] = (
    _page(
        "/",
        "Home",
        PageKind.HOME,
        "Zion Lifts' front page: what the company builds, who it builds for, and "
        "the work it is known for.",
        ("zion lifts", "home", "overview", "company", "elevators", "lifts", "solutions"),
        (
            ("Hero", "Zion Lifts — engineered to rise."),
            ("Our solutions", "The lift ranges Zion designs, installs and maintains."),
            ("Why Zion", "Engineering, safety and service commitments."),
            ("Industries", "Residential, commercial, hospital and industrial applications."),
            ("Proof", "Installed projects and their results."),
        ),
    ),
    _page(
        "/lifts",
        "Lifts",
        PageKind.PRODUCT_INDEX,
        "Every lift range Zion offers, with capacities, speeds, travel and the "
        "applications each one suits.",
        (
            "products",
            "product",
            "catalogue",
            "catalog",
            "range",
            "models",
            "passenger lift",
            "home lift",
            "residential lift",
            "villa lift",
            "hospital lift",
            "goods lift",
            "freight lift",
            "capsule lift",
            "dumbwaiter",
            "car stacker",
            "machine room less",
            "mrl",
            "specifications",
        ),
        (
            ("Range", "The full catalogue of Zion lift models."),
            ("Applications", "Which lift suits a home, an office, a hospital or a warehouse."),
            ("Specifications", "Capacity, speed, stops, drive, pit and headroom for each model."),
        ),
    ),
    _page(
        "/projects",
        "Projects",
        PageKind.PROJECT_INDEX,
        "Installations Zion has completed, with the brief, the constraint and the "
        "system that solved it.",
        (
            "projects",
            "case studies",
            "installations",
            "portfolio",
            "references",
            "work",
            "clients",
            "completed",
        ),
        (
            ("Featured", "Selected installations."),
            ("All projects", "The full list, filterable by category."),
        ),
    ),
    _page(
        "/about",
        "About",
        PageKind.CONTENT,
        "Who Zion Lifts is: history, engineering approach, the team and the "
        "manufacturing partners behind the products.",
        (
            "about",
            "company",
            "history",
            "who are you",
            "team",
            "leadership",
            "story",
            "values",
            "partners",
            "suppliers",
            "awards",
            "milestones",
            "founded",
            "experience",
        ),
        (
            ("Story", "How Zion Lifts started and how it has grown."),
            ("Engineering", "The engineering approach behind the products."),
            ("Team", "Leadership and departments."),
            ("Partners", "Component and drive partners."),
            ("Awards", "Recognition the company has received."),
        ),
    ),
    _page(
        "/contact",
        "Contact",
        PageKind.NAVIGATION,
        "How to reach Zion Lifts: enquiry form, service requests, phone, email and "
        "office addresses.",
        (
            "contact",
            "contact us",
            "get in touch",
            "reach",
            "phone",
            "call",
            "email",
            "address",
            "office",
            "location",
            "where are you",
            "map",
            "quote",
            "quotation",
            "enquiry",
            "enquire",
            "request",
            "service request",
            "support",
            "amc",
            "visit",
        ),
        (
            ("Enquiry", "Request a quotation or a site visit."),
            ("Service request", "Raise a maintenance or breakdown request."),
            ("Offices", "Addresses, phone numbers and opening hours."),
        ),
    ),
    _page(
        "/gallery",
        "Gallery",
        PageKind.CONTENT,
        "Photographs of finished cabins, interiors, finishes and installations.",
        (
            "gallery",
            "photos",
            "pictures",
            "images",
            "interiors",
            "finishes",
            "cabin",
            "look",
            "design",
            "see",
        ),
        (
            ("Interiors", "Cabin interiors and finishes."),
            ("Installations", "Completed installations on site."),
        ),
    ),
    _page(
        "/faq",
        "FAQ",
        PageKind.CONTENT,
        "Answers to the questions Zion is asked most often about buying, "
        "installing and maintaining a lift.",
        (
            "faq",
            "faqs",
            "questions",
            "frequently asked",
            "how long",
            "how much",
            "warranty",
            "maintenance",
            "amc",
            "installation time",
            "process",
        ),
        (("Questions", "Common questions about products, installation and service."),),
    ),
    _page(
        "/journal",
        "Journal",
        PageKind.JOURNAL,
        "Articles from Zion's engineers on lift technology, safety, standards and "
        "project practice.",
        (
            "journal",
            "blog",
            "articles",
            "news",
            "insights",
            "writing",
            "posts",
            "guides",
            "technology",
        ),
        (("Articles", "Long-form writing from the engineering team."),),
    ),
    _page(
        "/privacy",
        "Privacy policy",
        PageKind.LEGAL,
        "How Zion Lifts handles personal data submitted through the site.",
        ("privacy", "privacy policy", "data", "gdpr", "personal information"),
    ),
    _page(
        "/terms",
        "Terms of use",
        PageKind.LEGAL,
        "The terms under which this website may be used.",
        ("terms", "terms of use", "conditions", "legal"),
    ),
    _page(
        "/cookies",
        "Cookie policy",
        PageKind.LEGAL,
        "Which cookies this website sets and why.",
        ("cookies", "cookie policy", "tracking"),
    ),
)

STATIC_ROUTES: Final[frozenset[str]] = frozenset(page.route for page in STATIC_PAGES)


def route_exists(route: str, known_slugs: frozenset[str] | set[str] | None = None) -> bool:
    """Whether this path is a page on the site.

    A dynamic route additionally has to name a record that exists — which is
    what ``known_slugs`` carries. Without it, dynamic routes are refused rather
    than assumed: an index that has not loaded any products cannot vouch for a
    product URL, and vouching is the only thing this function is for.
    """
    if not route or not route.startswith("/"):
        return False
    path = route.split("#", 1)[0].split("?", 1)[0].rstrip("/") or "/"
    if path in STATIC_ROUTES:
        return True
    if not any(matcher.match(path) for matcher in _DYNAMIC_MATCHERS):
        return False
    if not known_slugs:
        return False
    return path.rsplit("/", 1)[-1] in known_slugs


__all__ = [
    "DYNAMIC_ROUTES",
    "STATIC_PAGES",
    "STATIC_ROUTES",
    "route_exists",
]
