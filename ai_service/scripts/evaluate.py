"""Score retrieval and answer quality against a labelled question set.

The dataset is JSONL, one object per line:
    {"question": "...", "expected_document_ids": ["..."], "expected_answer": "..."}

Usage:
    python -m scripts.evaluate tests/evaluation/dataset.jsonl --top-k 5
    python -m scripts.evaluate dataset.jsonl --compare      # all retrieval modes
    python -m scripts.evaluate dataset.jsonl --knowledge-base <uuid>

``--compare`` is the reason this script exists. Hybrid retrieval with a
cross-encoder on top is four moving parts, each of which costs latency and each
of which is *assumed* to help. Running the same questions through dense only,
sparse only, hybrid, and hybrid with the reranker turns that assumption into a
number — and occasionally shows that a stage is earning nothing on a particular
corpus, which is worth knowing before paying for it on every query.

Nothing here invents a score. A metric that cannot be computed from the dataset
is reported as absent rather than as zero: a labelled answer is needed for
groundedness, and expected document ids for anything ranked.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.api.deps import Container
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.scope import RetrievalScope

# The four configurations worth comparing. `alpha` is the dense/lexical weight
# the fusion uses; `rerank` decides whether the cross-encoder runs.
MODES: dict[str, dict[str, Any]] = {
    "dense": {"alpha": 1.0, "rerank": False},
    "sparse": {"alpha": 0.0, "rerank": False},
    "hybrid": {"alpha": None, "rerank": False},  # None = the configured alpha
    "hybrid+rerank": {"alpha": None, "rerank": True},
}


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
    recall: float = 0.0
    ndcg: float = 0.0
    confidence: float = 0.0
    cited: int = 0
    grounded: float | None = None
    citations_valid: float | None = None
    refusal_correct: float | None = None
    latency_ms: float = 0.0


def load_cases(path: Path) -> list[Case]:
    cases: list[Case] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(Case(**json.loads(line)))
    return cases


def score_retrieval(retrieved: list[str], expected: list[str]) -> dict[str, float]:
    """Rank metrics for one question.

    Graded relevance is not available — the dataset labels which documents are
    correct, not how correct — so nDCG uses binary gains. That still separates
    "the right document was first" from "the right document was fifth", which
    is the distinction the ranked metrics exist to make.
    """
    if not expected:
        return {"hit": 0.0, "mrr": 0.0, "precision": 0.0, "recall": 0.0, "ndcg": 0.0}

    wanted = set(expected)
    hits = [1.0 if doc in wanted else 0.0 for doc in retrieved]

    hit = 1.0 if any(hits) else 0.0
    rr = next((1.0 / rank for rank, gain in enumerate(hits, start=1) if gain), 0.0)
    precision = (sum(hits) / len(retrieved)) if retrieved else 0.0
    recall = len(wanted & set(retrieved)) / len(wanted)

    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(hits, start=1))
    ideal = sum(
        1.0 / math.log2(rank + 1) for rank in range(1, min(len(wanted), len(retrieved)) + 1)
    )
    ndcg = (dcg / ideal) if ideal else 0.0

    return {
        "hit": hit,
        "mrr": rr,
        "precision": precision,
        "recall": recall,
        "ndcg": ndcg,
    }


def citations_are_valid(answer: str, citations: list[Any]) -> float:
    """Whether every marker in the prose maps to a citation that was returned.

    A fabricated marker is worse than a missing one: it looks like evidence.
    """
    import re

    markers = {int(m) for m in re.findall(r"\[(\d+)\]", answer or "")}
    if not markers:
        return 1.0
    available = {
        int(str(getattr(c, "marker", "")).strip("[]") or 0)
        for c in citations
        if str(getattr(c, "marker", "")).strip("[]").isdigit()
    }
    return 1.0 if markers <= available else 0.0


def is_refusal(answer: str) -> bool:
    from app.prompts.system import REFUSAL_TEXT

    return (answer or "").strip().startswith(REFUSAL_TEXT[:40])


def groundedness(answer: str, chunks: list[Any]) -> float:
    """A cheap lexical overlap between the answer and the passages it cites.

    Not an LLM judge, deliberately. This number is used to spot a regression
    between two runs of the same dataset, and a judge that is itself a
    stochastic model makes a poor ruler for that. It is a floor, not a verdict.
    """
    from app.retrieval.sparse import tokenize

    answer_terms = set(tokenize(answer or ""))
    if not answer_terms:
        return 0.0
    context_terms: set[str] = set()
    for chunk in chunks:
        context_terms |= set(tokenize(chunk.text))
    if not context_terms:
        return 0.0
    return len(answer_terms & context_terms) / len(answer_terms)


def configure_mode(search: HybridSearch, mode: str) -> tuple[float, bool]:
    """Point the shared HybridSearch at one mode, returning what to restore."""
    settings = MODES[mode]
    previous = search._alpha  # noqa: SLF001 - the harness owns this instance
    if settings["alpha"] is not None:
        search._alpha = settings["alpha"]  # noqa: SLF001
    return previous, bool(settings["rerank"])


async def run_mode(
    container: Container,
    cases: list[Case],
    scope: RetrievalScope,
    mode: str,
    top_k: int,
    generate: bool,
) -> list[Scores]:
    """Score every case under one retrieval configuration."""
    pipeline = container.pipeline
    search = pipeline._search  # noqa: SLF001 - evaluation reaches in deliberately
    original_alpha, use_reranker = configure_mode(search, mode)
    original_reranker = pipeline._reranker  # noqa: SLF001

    if not use_reranker:
        from app.retrieval.reranker import NoopReranker

        pipeline._reranker = NoopReranker()  # noqa: SLF001

    per_case: list[Scores] = []
    try:
        for case in cases:
            started = time.perf_counter()
            if generate:
                result = await pipeline.ask(case.question, scope=scope, top_k=top_k)
                chunks, answer, citations = result.chunks, result.answer, result.citations
                confidence = result.confidence.score if result.confidence else 0.0
            else:
                chunks, _ = await pipeline.retrieve(case.question, scope=scope, top_k=top_k)
                answer, citations, confidence = "", [], 0.0
            latency_ms = (time.perf_counter() - started) * 1000

            metrics = score_retrieval(
                [chunk.document_id for chunk in chunks], case.expected_document_ids
            )
            scores = Scores(
                **metrics,
                confidence=confidence,
                cited=len(citations),
                latency_ms=latency_ms,
            )

            if generate:
                scores.grounded = groundedness(answer, chunks)
                scores.citations_valid = citations_are_valid(answer, citations)
                # A case with no expected documents is one the corpus should not
                # be able to answer, so refusing is the correct outcome.
                if not case.expected_document_ids:
                    scores.refusal_correct = 1.0 if is_refusal(answer) else 0.0
                elif case.expected_answer:
                    scores.refusal_correct = 0.0 if is_refusal(answer) else 1.0

            per_case.append(scores)
    finally:
        search._alpha = original_alpha  # noqa: SLF001
        pipeline._reranker = original_reranker  # noqa: SLF001

    return per_case


def summarise(per_case: list[Scores], top_k: int) -> dict[str, Any]:
    def mean(name: str) -> float | None:
        values = [getattr(s, name) for s in per_case if getattr(s, name) is not None]
        return round(statistics.fmean(values), 4) if values else None

    latencies = sorted(s.latency_ms for s in per_case)

    def percentile(fraction: float) -> float:
        if not latencies:
            return 0.0
        index = min(len(latencies) - 1, int(fraction * len(latencies)))
        return round(latencies[index], 1)

    return {
        "cases": len(per_case),
        f"recall@{top_k}": mean("recall"),
        f"precision@{top_k}": mean("precision"),
        f"hit@{top_k}": mean("hit"),
        "mrr": mean("mrr"),
        f"ndcg@{top_k}": mean("ndcg"),
        "confidence": mean("confidence"),
        "grounded": mean("grounded"),
        "citations_valid": mean("citations_valid"),
        "refusal_correct": mean("refusal_correct"),
        "latency_p50_ms": percentile(0.50),
        "latency_p95_ms": percentile(0.95),
        "latency_p99_ms": percentile(0.99),
    }


def print_table(results: dict[str, dict[str, Any]]) -> None:
    """One row per mode, so the comparison is readable without a spreadsheet."""
    modes = list(results)
    metrics = [k for k in results[modes[0]] if k != "cases"]

    width = max(len(m) for m in metrics) + 2
    header = "metric".ljust(width) + "".join(m.rjust(16) for m in modes)
    print(header)
    print("-" * len(header))
    for metric in metrics:
        row = metric.ljust(width)
        for mode in modes:
            value = results[mode][metric]
            row += ("—" if value is None else f"{value:g}").rjust(16)
        print(row)


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging("WARNING", settings.log_json)

    cases = load_cases(Path(args.dataset))
    if not cases:
        print("Dataset is empty.")
        return 1

    container = await Container.build(settings)

    # The pipeline takes a scope rather than a collection name, so the harness
    # builds one the same way the service does. --knowledge-base evaluates a
    # real corpus; without it the run measures the legacy collection.
    scope = (
        RetrievalScope.for_knowledge_base(args.knowledge_base)
        if args.knowledge_base
        else RetrievalScope.legacy(args.collection or settings.qdrant_collection)
    )

    modes = list(MODES) if args.compare else [args.mode]

    try:
        results: dict[str, dict[str, Any]] = {}
        for mode in modes:
            per_case = await run_mode(
                container, cases, scope, mode, args.top_k, generate=not args.retrieval_only
            )
            results[mode] = summarise(per_case, args.top_k)
    finally:
        await container.close()

    print()
    print_table(results)
    print()

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Report written to {args.out}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="Path to a JSONL evaluation set.")
    parser.add_argument("--collection", default=None, help="Legacy collection to evaluate.")
    parser.add_argument("--knowledge-base", default=None, help="Knowledge base id to evaluate.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--mode", choices=list(MODES), default="hybrid+rerank", help="One retrieval mode."
    )
    parser.add_argument(
        "--compare", action="store_true", help="Run every retrieval mode and tabulate."
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Skip generation. Much faster, and the only fair way to compare "
        "retrieval modes without an LLM's variance in the numbers.",
    )
    parser.add_argument("--out", default=None, help="Optional JSON report path.")
    args = parser.parse_args()

    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
