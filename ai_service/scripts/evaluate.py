"""Score retrieval and answer quality against a labelled question set.

The dataset is JSONL, one object per line:
    {"question": "...", "expected_document_ids": ["..."], "expected_answer": "..."}

Usage:
    python -m scripts.evaluate tests/evaluation/dataset.jsonl --top-k 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from app.api.deps import Container
from app.core.config import get_settings
from app.core.logging import configure_logging


@dataclass(slots=True)
class Case:
    question: str
    expected_document_ids: list[str] = field(default_factory=list)
    expected_answer: str | None = None


@dataclass(slots=True)
class Scores:
    hit: float = 0.0
    mrr: float = 0.0
    precision: float = 0.0
    confidence: float = 0.0
    cited: int = 0
    latency_ms: float = 0.0


def load_cases(path: Path) -> list[Case]:
    cases: list[Case] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(Case(**json.loads(line)))
    return cases


def score_retrieval(retrieved: list[str], expected: list[str]) -> tuple[float, float, float]:
    """Hit@k, reciprocal rank, and precision@k for one question."""
    if not expected:
        return 0.0, 0.0, 0.0
    wanted = set(expected)
    hit = 1.0 if wanted & set(retrieved) else 0.0
    rr = next(
        (1.0 / rank for rank, doc in enumerate(retrieved, start=1) if doc in wanted), 0.0
    )
    precision = sum(1 for doc in retrieved if doc in wanted) / len(retrieved) if retrieved else 0.0
    return hit, rr, precision


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging("WARNING", settings.log_json)

    cases = load_cases(Path(args.dataset))
    if not cases:
        print("Dataset is empty.")
        return 1

    container = await Container.build(settings)
    per_case: list[Scores] = []

    try:
        for i, case in enumerate(cases, start=1):
            result = await container.pipeline.ask(
                case.question, collection=args.collection, top_k=args.top_k
            )
            retrieved = [chunk.document_id for chunk in result.chunks]
            hit, rr, precision = score_retrieval(retrieved, case.expected_document_ids)

            per_case.append(
                Scores(
                    hit=hit,
                    mrr=rr,
                    precision=precision,
                    confidence=result.confidence.score if result.confidence else 0.0,
                    cited=len(result.citations),
                    latency_ms=result.took_ms,
                )
            )
            print(f"[{i}/{len(cases)}] hit={hit:.0f} rr={rr:.2f} {case.question[:60]}")
    finally:
        await container.close()

    def mean(attr: str) -> float:
        return statistics.fmean(getattr(s, attr) for s in per_case)

    print("\n=== Evaluation summary ===")
    print(f"cases            {len(per_case)}")
    print(f"hit@{args.top_k}            {mean('hit'):.3f}")
    print(f"MRR              {mean('mrr'):.3f}")
    print(f"precision@{args.top_k}      {mean('precision'):.3f}")
    print(f"mean confidence  {mean('confidence'):.3f}")
    print(f"mean citations   {mean('cited'):.2f}")
    print(f"p50 latency      {statistics.median(s.latency_ms for s in per_case):.0f} ms")

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "cases": len(per_case),
                    "hit_at_k": mean("hit"),
                    "mrr": mean("mrr"),
                    "precision_at_k": mean("precision"),
                    "mean_confidence": mean("confidence"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWrote {args.out}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG quality.")
    parser.add_argument("dataset", help="Path to a JSONL evaluation set.")
    parser.add_argument("--collection", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", default=None, help="Optional JSON report path.")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
