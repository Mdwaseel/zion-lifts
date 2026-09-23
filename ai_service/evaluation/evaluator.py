"""Score the assistant against the labelled question set.

Two modes, because two very different things are worth measuring and only one
of them can run without infrastructure.

``--offline`` (the default) exercises the router, the security layer, the
website index and the answer strategy. No model, no Qdrant, no network. It
measures routing accuracy, refusal accuracy in both directions, clarification
accuracy, retrieval gating and link validity — which between them cover every
decision that determines whether an answer is *allowed* to be wrong. It runs in
under a second and belongs in CI.

``--live`` runs the real pipeline through the real container: a real corpus, a
real model, real latency. It adds retrieval ranking metrics and the answer-level
proxies, and it needs a configured Qdrant and at least one LLM credential. It is
not run in CI, and the report says which mode produced it so the two are never
confused.

    python -m evaluation.evaluator
    python -m evaluation.evaluator --live --knowledge-base <uuid>
    python -m evaluation.evaluator --json report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.query_router import QueryRouter
from app.query_router.intents import Source
from app.website.builder import build_index
from app.website.index import WebsiteIndex
from evaluation import answer_metrics as answers
from evaluation import retrieval_metrics as ranking

DATASET = Path(__file__).with_name("dataset.json")

# Behaviours that mean the assistant declined to answer the question as asked.
_REFUSING = {"refused", "unverified"}


@dataclass(slots=True)
class Case:
    id: str
    category: str
    question: str
    expected_intent: str | None = None
    must_refuse: bool | None = None
    must_not_refuse: bool | None = None
    expects_clarification: bool | None = None
    expects_retrieval: bool | None = None
    allowed_routes: list[str] | None = None
    requires_evidence: bool = False
    expected_document_ids: list[str] = field(default_factory=list)
    #: Why a label is what it is, when that was not obvious. Carried so a
    #: label correction leaves a trace in the file rather than in a commit
    #: message nobody reads next to the failure.
    label_note: str | None = None

    @property
    def refusal_label(self) -> bool | None:
        """The two labels folded into one tri-state.

        ``must_not_refuse`` exists as a separate field in the dataset because it
        reads correctly there, but a case never sets both and the metric wants
        one value.
        """
        if self.must_refuse is not None:
            return self.must_refuse
        if self.must_not_refuse is not None:
            return not self.must_not_refuse
        return None


@dataclass(slots=True)
class CaseResult:
    case: Case
    intent: str
    behaviour: str
    urls: list[str] = field(default_factory=list)
    answer: str = ""
    cited_markers: list[int] = field(default_factory=list)
    available_markers: list[int] = field(default_factory=list)
    retrieved_ids: list[str] = field(default_factory=list)
    took_ms: float = 0.0

    @property
    def refused(self) -> bool:
        return self.behaviour in _REFUSING


def load_cases(path: Path = DATASET) -> list[Case]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Case(**case) for case in payload["cases"]]


# --------------------------------------------------------------------- offline


def run_offline(cases: list[Case], index: WebsiteIndex) -> list[CaseResult]:
    """Route every case and record the decisions, without answering any of them.

    What this can and cannot see is worth being precise about. It sees the
    intent, whether the request was terminated by the security layer, whether
    clarification would be asked, and whether document retrieval would run. It
    does not see an answer, so nothing here can report faithfulness — and does
    not pretend to.
    """
    from app.orchestration import answer_strategy, references
    from app.orchestration.evidence import EvidenceBundle

    router = QueryRouter()
    results: list[CaseResult] = []

    for case in cases:
        decision = router.route(case.question)

        if decision.is_terminal:
            behaviour = "refused"
        elif answer_strategy.is_ambiguous(decision):
            behaviour = "clarify"
        else:
            behaviour = "answer"

        # The links this question would actually be offered — through the same
        # search, the same scoring floors and the same verification the live
        # pipeline uses. Re-implementing the selection here would measure a
        # system nobody runs, which is the classic way an evaluation harness
        # comes to disagree with production and be believed anyway.
        urls: list[str] = []
        if decision.plan.wants(Source.WEBSITE) and not decision.is_terminal:
            bundle = EvidenceBundle()
            bundle.pages = [
                (hit.page, hit.section, hit.score)
                for hit in index.search(
                    decision.query.retrieval,
                    limit=decision.plan.max_related_pages,
                    kinds=set(decision.plan.page_kinds) or None,
                )
            ]
            urls = [
                link.url for link in references.build_related_pages(decision, bundle, index, [])
            ]

        results.append(
            CaseResult(
                case=case,
                intent=str(decision.intent),
                behaviour=behaviour,
                urls=urls,
            )
        )
    return results


# ------------------------------------------------------------------------ live


async def run_live(cases: list[Case], knowledge_base: str | None) -> list[CaseResult]:
    """Answer every case through the real container.

    Builds the same object graph the API builds, so what is measured is what
    ships. Requires a reachable Qdrant and at least one configured provider; it
    fails loudly rather than degrading, because a live evaluation that quietly
    fell back to the static index would report numbers for a system nobody runs.
    """
    import time

    from app.api.deps import Container
    from app.core.config import get_settings
    from app.retrieval.scope import RetrievalScope

    settings = get_settings()
    container = await Container.build(settings)
    if container.assistant is None:
        raise RuntimeError("QUERY_ROUTING_ENABLED is false; there is nothing to evaluate")

    scope = (
        RetrievalScope.for_knowledge_base(knowledge_base)
        if knowledge_base
        else RetrievalScope.legacy(settings.qdrant_collection)
    )

    results: list[CaseResult] = []
    try:
        for case in cases:
            started = time.perf_counter()
            result = await container.assistant.ask(case.question, scope)
            took = (time.perf_counter() - started) * 1000
            results.append(
                CaseResult(
                    case=case,
                    intent=result.intent,
                    behaviour=result.behaviour,
                    urls=[p.url for p in result.related_pages]
                    + [c.url for c in result.citations if c.url],
                    answer=result.answer,
                    cited_markers=[int(c.marker.strip("[]")) for c in result.citations],
                    available_markers=[i.marker for i in result.bundle.items],
                    retrieved_ids=[i.document_id for i in result.bundle.documents],
                    took_ms=took,
                )
            )
    finally:
        await container.close()
    return results


# --------------------------------------------------------------------- scoring


def score(results: list[CaseResult], index: WebsiteIndex, live: bool) -> dict[str, Any]:
    """Turn per-case results into the report."""
    routing = [
        (r.case.expected_intent == r.intent)
        for r in results
        if r.case.expected_intent is not None
    ]
    refusals = [
        answers.refusal_is_correct(r.answer, r.refused, r.case.refusal_label) for r in results
    ]
    clarifications = [
        (r.behaviour == "clarify") is r.case.expects_clarification
        for r in results
        if r.case.expects_clarification is not None
    ]
    gating = [
        (bool(r.retrieved_ids) is r.case.expects_retrieval)
        for r in results
        if live and r.case.expects_retrieval is not None
    ]

    link_valid = [answers.links_are_real(r.urls, index) for r in results if r.urls]
    link_expected = [
        ok
        for ok in (answers.links_are_expected(r.urls, r.case.allowed_routes) for r in results)
        if ok is not None
    ]

    report: dict[str, Any] = {
        "mode": "live" if live else "offline",
        "cases": len(results),
        "routing_accuracy": _share(routing),
        "refusal_accuracy": _share([r for r in refusals if r is not None]),
        "clarification_accuracy": _share(clarifications),
        "website_link_validity": _share(link_valid),
        "website_link_relevance": _share(link_expected),
        "by_category": _by_category(results),
        "failures": _failures(results, index),
    }

    if live:
        report["retrieval_gating_accuracy"] = _share(gating)
        report["citation_validity"] = _share(
            [answers.citations_resolve(r.answer, r.available_markers) for r in results]
        )
        unsupported = sum(
            answers.unsupported_company_claims(r.answer, r.cited_markers)
            for r in results
            if not r.refused
        )
        answered = sum(1 for r in results if not r.refused)
        report["unsupported_company_claims_per_answer"] = answers.rate(unsupported, answered)
        report["latency_ms"] = {
            "mean": round(sum(r.took_ms for r in results) / len(results), 1) if results else None,
            "max": round(max((r.took_ms for r in results), default=0.0), 1),
        }
        labelled = [r for r in results if r.case.expected_document_ids]
        if labelled:
            report["retrieval"] = {
                "precision@5": ranking.mean(
                    [
                        ranking.precision_at_k(r.retrieved_ids, r.case.expected_document_ids, 5)
                        for r in labelled
                    ]
                ),
                "recall@5": ranking.mean(
                    [
                        ranking.recall_at_k(r.retrieved_ids, r.case.expected_document_ids, 5)
                        for r in labelled
                    ]
                ),
                "mrr": ranking.mean(
                    [
                        ranking.reciprocal_rank(r.retrieved_ids, r.case.expected_document_ids)
                        for r in labelled
                    ]
                ),
                "ndcg@5": ranking.mean(
                    [
                        ranking.ndcg_at_k(r.retrieved_ids, r.case.expected_document_ids, 5)
                        for r in labelled
                    ]
                ),
            }
        else:
            # Said rather than reported as zero: no case in the dataset carries
            # labelled document ids, so there is nothing to rank against.
            report["retrieval"] = "not measured: no expected_document_ids in the dataset"

    return report


def _share(values: list[bool]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _by_category(results: list[CaseResult]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        buckets[result.case.category].append(result)

    summary = {}
    for category, group in sorted(buckets.items()):
        routing = [
            r.case.expected_intent == r.intent for r in group if r.case.expected_intent
        ]
        refusal = [
            ok
            for ok in (
                answers.refusal_is_correct(r.answer, r.refused, r.case.refusal_label)
                for r in group
            )
            if ok is not None
        ]
        summary[category] = {
            "cases": len(group),
            "routing_accuracy": _share(routing),
            "refusal_accuracy": _share(refusal),
        }
    return summary


def _failures(results: list[CaseResult], index: WebsiteIndex) -> list[dict[str, str]]:
    """Every case that missed, named. A score with no failure list is a score
    nobody can act on."""
    failures = []
    for result in results:
        case = result.case
        reasons = []
        if case.expected_intent and case.expected_intent != result.intent:
            reasons.append(f"intent {result.intent} != {case.expected_intent}")
        if case.refusal_label is not None and result.refused is not case.refusal_label:
            reasons.append("refused" if result.refused else "did not refuse")
        if case.expects_clarification is not None and (
            (result.behaviour == "clarify") is not case.expects_clarification
        ):
            reasons.append(f"behaviour {result.behaviour}")
        if result.urls and not answers.links_are_real(result.urls, index):
            reasons.append("suggested a URL that does not exist")
        allowed = answers.links_are_expected(result.urls, case.allowed_routes)
        if allowed is False:
            reasons.append(f"links {result.urls} outside {case.allowed_routes}")
        if reasons:
            failures.append({"id": case.id, "question": case.question, "why": "; ".join(reasons)})
    return failures


def render(report: dict[str, Any]) -> str:
    lines = [
        f"Assistant evaluation — {report['mode']} mode, {report['cases']} cases",
        "=" * 60,
    ]
    for key in (
        "routing_accuracy",
        "refusal_accuracy",
        "clarification_accuracy",
        "retrieval_gating_accuracy",
        "website_link_validity",
        "website_link_relevance",
        "citation_validity",
        "unsupported_company_claims_per_answer",
    ):
        if key in report:
            value = report[key]
            lines.append(f"  {key:44s} {'n/a' if value is None else value}")

    if "latency_ms" in report:
        lines.append(f"  {'latency_ms (mean/max)':44s} {report['latency_ms']}")
    if "retrieval" in report:
        lines.append(f"  {'retrieval':44s} {report['retrieval']}")

    lines.append("")
    lines.append("By category")
    for category, stats in report["by_category"].items():
        lines.append(
            f"  {category:18s} n={stats['cases']:<3} "
            f"routing={stats['routing_accuracy']} refusal={stats['refusal_accuracy']}"
        )

    failures = report["failures"]
    lines.append("")
    lines.append(f"Failures ({len(failures)})")
    for failure in failures:
        lines.append(f"  {failure['id']:10s} {failure['why']}")
        lines.append(f"             {failure['question']}")
    if not failures:
        lines.append("  none")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument(
        "--live",
        action="store_true",
        help="answer every case through the real pipeline (needs Qdrant and an LLM key)",
    )
    parser.add_argument("--knowledge-base", default=None)
    parser.add_argument("--json", type=Path, default=None, help="also write the report as JSON")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="exit non-zero if routing or refusal accuracy falls below this",
    )
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    index = await build_index(None)  # static routes; the live run rebuilds its own

    if args.live:
        results = await run_live(cases, args.knowledge_base)
    else:
        results = run_offline(cases, index)

    report = score(results, index, live=args.live)
    print(render(report))

    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.fail_under is not None:
        for key in ("routing_accuracy", "refusal_accuracy"):
            value = report.get(key)
            if value is not None and value < args.fail_under:
                print(f"\nFAIL: {key} {value} < {args.fail_under}")
                return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(asyncio.run(main()))
