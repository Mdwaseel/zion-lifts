"""PDF text extraction, page by page so page numbers survive into citations."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

from app.core.constants import SourceType
from app.core.logging import get_logger
from app.ingestion.loaders.text_loader import LoadedDocument

logger = get_logger(__name__)

PAGE_SEPARATOR = "\n\n[[page:{page}]]\n\n"


class PdfLoader:
    source_type = SourceType.PDF

    def _extract(self, stream: io.BytesIO) -> tuple[str, int]:
        from pypdf import PdfReader

        reader = PdfReader(stream)
        parts: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                parts.append(PAGE_SEPARATOR.format(page=number) + text)
        return "\n".join(parts), len(reader.pages)

    async def load_bytes(self, data: bytes, filename: str) -> LoadedDocument:
        text, pages = await asyncio.to_thread(self._extract, io.BytesIO(data))
        if not text.strip():
            logger.warning("pdf produced no text", extra={"filename": filename})
        return LoadedDocument(
            text=text,
            source=filename,
            source_type=self.source_type,
            metadata={"filename": filename, "pages": pages, "bytes": len(data)},
        )

    async def load_path(self, path: str | Path) -> LoadedDocument:
        p = Path(path)
        return await self.load_bytes(p.read_bytes(), p.name)
