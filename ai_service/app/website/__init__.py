"""The website, as something the assistant can search and link into.

Four pieces, each with one job:

    routes.py     the route table — the only list of URLs that may be produced
    models.py     what a page and a section are
    builder.py    turning the site's own content API into pages
    index.py      searching them, and verifying that a URL is real
    provider.py   holding the current index and refreshing it off the hot path

The separation exists so the guarantee is auditable: exactly one function,
:meth:`WebsiteIndex.verify`, decides whether a link may be shown, and it can
only say yes about a page the index is actually holding.
"""

from __future__ import annotations

from app.website.index import EMPTY_INDEX, PageHit, WebsiteIndex
from app.website.models import PageKind, WebsitePage, WebsiteSection
from app.website.provider import WebsiteIndexProvider
from app.website.routes import STATIC_PAGES, route_exists

__all__ = [
    "EMPTY_INDEX",
    "STATIC_PAGES",
    "PageHit",
    "PageKind",
    "WebsiteIndex",
    "WebsiteIndexProvider",
    "WebsitePage",
    "WebsiteSection",
    "route_exists",
]
