"""Bulk-ingest local files, directories or URLs into a collection.

Usage:
    python -m scripts.ingest ./docs --collection handbook
    python -m scripts.ingest https://example.com/page --tag reference
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.api.deps import Container
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger("ingest")

SUPPORTED = {".pdf", ".txt", ".md", ".markdown", ".rst", ".csv", ".json"}


def expand(target: str) -> list[str]:
    if target.startswith(("http://", "https://")):
        return [target]
    path = Path(target)
    if path.is_file():
        return [str(path)]
    if path.is_dir():
        return sorted(
            str(p) for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED
        )
    raise FileNotFoundError(f"No such file, directory or URL: {target}")


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    container = await Container.build(settings)

    targets: list[str] = []
    for raw in args.targets:
        targets.extend(expand(raw))

    if not targets:
        logger.warning("nothing to ingest")
        return 1

    logger.info("ingesting %d target(s)", len(targets))
    metadata = {"tags": args.tag} if args.tag else {}
    failures = 0

    try:
        for i, target in enumerate(targets, start=1):
            try:
                if target.startswith(("http://", "https://")):
                    result = await container.ingestion.ingest_url(target, metadata, args.collection)
                else:
                    path = Path(target)
                    result = await container.ingestion.ingest_file(
                        path.read_bytes(), path.name, metadata, args.collection
                    )
                print(
                    f"[{i}/{len(targets)}] {target} -> "
                    f"{result.chunk_count} chunks ({result.document_id})"
                )
            except Exception as exc:
                failures += 1
                print(f"[{i}/{len(targets)}] FAILED {target}: {exc}", file=sys.stderr)
    finally:
        await container.close()

    print(f"\nDone. {len(targets) - failures} succeeded, {failures} failed.")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest documents into the vector store.")
    parser.add_argument("targets", nargs="+", help="Files, directories or URLs.")
    parser.add_argument("--collection", default=None, help="Target collection.")
    parser.add_argument("--tag", action="append", default=[], help="Repeatable metadata tag.")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
