"""Fetch a URL and reduce it to readable body text."""

from __future__ import annotations

import re

import httpx

from app.core.constants import SourceType
from app.core.logging import get_logger
from app.ingestion.loaders.text_loader import LoadedDocument

logger = get_logger(__name__)

_DROP_TAGS = ("script", "style", "nav", "footer", "header", "aside", "form", "noscript")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class WebLoader:
    source_type = SourceType.WEB

    def __init__(self, timeout: float = 20.0, user_agent: str = "ai-service/1.0") -> None:
        self._timeout = timeout
        self._headers = {"User-Agent": user_agent}

    def _to_text(self, html: str) -> tuple[str, str | None]:
        title_match = _TITLE_RE.search(html)
        title = title_match.group(1).strip() if title_match else None
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(_DROP_TAGS):
                tag.decompose()
            text = soup.get_text(separator="\n")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
        except ImportError:  # graceful fallback when bs4 is absent
            text = re.sub(r"<[^>]+>", " ", html)
        return text, title

    async def load_url(self, url: str) -> LoadedDocument:
        async with httpx.AsyncClient(
            timeout=self._timeout, headers=self._headers, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "html" in content_type:
            text, title = self._to_text(response.text)
        else:
            text, title = response.text, None

        return LoadedDocument(
            text=text,
            source=url,
            source_type=self.source_type,
            metadata={"url": url, "title": title, "content_type": content_type},
        )
