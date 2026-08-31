"""Plain text / markdown loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import SourceType


@dataclass(slots=True)
class LoadedDocument:
    """Raw text plus provenance, before cleaning and chunking."""

    text: str
    source: str
    source_type: SourceType
    metadata: dict[str, Any] = field(default_factory=dict)


class TextLoader:
    source_type = SourceType.TEXT

    def load_string(self, text: str, source: str = "inline") -> LoadedDocument:
        return LoadedDocument(text=text, source=source, source_type=self.source_type)

    def load_path(self, path: str | Path, encoding: str = "utf-8") -> LoadedDocument:
        p = Path(path)
        raw = p.read_text(encoding=encoding, errors="replace")
        return LoadedDocument(
            text=raw,
            source=str(p),
            source_type=self.source_type,
            metadata={"filename": p.name, "bytes": p.stat().st_size},
        )

    def load_bytes(self, data: bytes, filename: str, encoding: str = "utf-8") -> LoadedDocument:
        return LoadedDocument(
            text=data.decode(encoding, errors="replace"),
            source=filename,
            source_type=self.source_type,
            metadata={"filename": filename, "bytes": len(data)},
        )
