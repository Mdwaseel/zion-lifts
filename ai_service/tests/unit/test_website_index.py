"""The website index: what it finds, and what it refuses to vouch for.

The refusal tests are the important ones. A link the assistant offers is a
promise that a page exists, and the only thing standing behind that promise is
:meth:`WebsiteIndex.verify` — so it is tested against invented routes, against
routes that exist in the manifest but hold no content, and against fragments
nobody declared.
"""

from __future__ import annotations

import httpx
import pytest

from app.website.builder import SiteContent, build_pages, clean, fetch_content
from app.website.index import WebsiteIndex
from app.website.models import PageKind, WebsitePage, WebsiteSection
from app.website.provider import WebsiteIndexProvider
from app.website.routes import STATIC_PAGES, route_exists

LIFTS = [
    {
        "slug": "home-lift",
        "name": "Aria Home Lift",
        "tagline": "A quiet lift for a family home.",
        "summary": "A compact residential lift for villas and duplexes, 250 kg, 0.3 m/s.",
        "capacity": "250 kg",
        "speed": "0.3 m/s",
        "machine_room": "Not required",
        "applications": [{"name": "Villas"}, {"name": "Duplex homes"}],
    },
    {
        "slug": "hospital-lift",
        "name": "Meridian Hospital Lift",
        "tagline": "Stretcher-rated, with levelling for trolleys.",
        "summary": "A hospital lift sized for a stretcher and an attending team.",
        "capacity": "1600 kg",
        "applications": [{"name": "Hospitals"}],
    },
]

OFFICES = [
    {
        "name": "Head office",
        "address": "Plot 14, Jubilee Hills",
        "city": "Hyderabad",
        "locality": "Jubilee Hills",
        "phone": "+91 91000 00000",
        "hours": "Mon–Sat, 9am–6pm",
    }
]


def build_index() -> WebsiteIndex:
    content = SiteContent(lifts=LIFTS, projects=[], journal=[], offices=OFFICES, site={})
    return WebsiteIndex(build_pages(content), generated_at=1.0)


class TestRouteManifest:
    def test_static_routes_exist(self):
        for page in STATIC_PAGES:
            assert route_exists(page.route)

    def test_an_invented_route_does_not_exist(self):
        assert not route_exists("/products/magic-lift")
        assert not route_exists("/pricing")

    def test_a_dynamic_route_needs_a_real_slug(self):
        assert not route_exists("/lifts/does-not-exist")
        assert route_exists("/lifts/home-lift", {"home-lift"})

    def test_a_route_without_a_leading_slash_is_refused(self):
        assert not route_exists("lifts")
        assert not route_exists("https://example.com/lifts")


class TestSearch:
    def test_a_product_question_reaches_the_product_page(self):
        hits = build_index().search("home lift for a villa", limit=3)
        assert hits
        assert hits[0].page.route in {"/lifts/home-lift", "/lifts"}

    def test_a_navigational_question_reaches_the_contact_page(self):
        hits = build_index().search("where is your office and phone number", limit=3)
        assert hits[0].page.route == "/contact"

    def test_the_office_address_is_searchable_after_a_build(self):
        hits = build_index().search("Jubilee Hills office", limit=2)
        assert any(h.page.route == "/contact" for h in hits)

    def test_filtering_by_kind_excludes_everything_else(self):
        hits = build_index().search("lift", limit=5, kinds={PageKind.PRODUCT})
        assert hits
        assert all(h.page.kind is PageKind.PRODUCT for h in hits)

    def test_an_unmatchable_query_returns_nothing(self):
        assert build_index().search("xyzzy plugh", limit=3) == []


class TestVerification:
    def test_a_real_page_verifies(self):
        assert build_index().verify("/lifts/home-lift") == "/lifts/home-lift"

    def test_an_invented_page_does_not(self):
        assert build_index().verify("/lifts/magic-lift") is None
        assert build_index().verify("/pricing") is None

    def test_an_unloaded_product_page_does_not_verify(self):
        # The route shape is valid and the manifest allows it, but no such lift
        # was published — so the index cannot vouch for it.
        empty = WebsiteIndex(build_pages(None))
        assert empty.verify("/lifts/home-lift") is None
        assert empty.verify("/lifts") == "/lifts"

    def test_an_undeclared_fragment_is_dropped_not_kept(self):
        index = WebsiteIndex(
            [
                WebsitePage(
                    route="/contact",
                    title="Contact",
                    kind=PageKind.NAVIGATION,
                    sections=(WebsiteSection("Offices", "…", anchor="offices"),),
                )
            ]
        )
        assert index.verify("/contact#pricing") == "/contact"
        assert index.verify("/contact#offices") == "/contact#offices"

    def test_a_page_with_an_impossible_route_is_never_indexed(self):
        index = WebsiteIndex([WebsitePage(route="/not-a-real-page", title="Nope")])
        assert index.is_empty


class TestBuilder:
    def test_markup_is_stripped_and_bounded(self):
        assert clean("<p>Hello <b>world</b></p>") == "Hello world"
        assert len(clean("x" * 5000)) <= 600

    def test_a_record_without_a_slug_is_skipped(self):
        content = SiteContent(
            lifts=[{"name": "No slug"}], projects=[], journal=[], offices=[], site={}
        )
        routes = {p.route for p in build_pages(content)}
        assert not any(r.startswith("/lifts/") for r in routes)

    def test_no_backend_still_produces_the_static_pages(self):
        pages = build_pages(None)
        assert {p.route for p in pages} >= {"/", "/lifts", "/contact"}

    async def test_a_failing_endpoint_does_not_lose_the_others(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/projects/"):
                return httpx.Response(500)
            if request.url.path.endswith("/lifts/"):
                return httpx.Response(200, json=LIFTS)
            if request.url.path.endswith("/site/"):
                return httpx.Response(200, json={"city": "Hyderabad"})
            return httpx.Response(200, json=[])

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            content = await fetch_content("http://backend", client)

        assert content.partial
        assert len(content.lifts) == 2
        assert content.projects == []


class TestProvider:
    async def test_the_static_index_is_available_before_any_build(self):
        provider = WebsiteIndexProvider(base_url=None)
        assert not provider.current.is_empty
        assert provider.current.verify("/contact") == "/contact"

    async def test_a_failed_refresh_keeps_the_previous_index(self, monkeypatch):
        provider = WebsiteIndexProvider(base_url="http://backend")
        before = provider.current

        async def explode(*args, **kwargs):
            raise RuntimeError("backend is down")

        monkeypatch.setattr("app.website.provider.build_index", explode)
        after = await provider.refresh()
        assert after is before


@pytest.mark.parametrize("route", ["/", "/lifts", "/projects", "/about", "/contact", "/faq"])
def test_every_advertised_route_is_in_the_index(route):
    assert WebsiteIndex(build_pages(None)).verify(route) == route
