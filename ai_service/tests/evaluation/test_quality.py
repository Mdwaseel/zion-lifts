"""Quality benchmarks. Marked so they stay out of the default run: pytest -m evaluation

The scoring functions are tested here rather than in the unit suite because they
belong to the evaluation harness: they decide what "better retrieval" means, and
a bug in one of them would show up as a confident, wrong comparison between
retrieval modes rather than as a failure anyone would notice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.evaluate import (
    MODES,
    Case,
    citations_are_valid,
    groundedness,
    score_retrieval,
    summarise,
)

DATASET = Path(__file__).parent / "dataset.jsonl"

pytestmark = pytest.mark.evaluation


class Chunk:
    def __init__(self, text: str) -> None:
        self.text = text


class Citation:
    def __init__(self, marker: str) -> None:
        self.marker = marker


def test_dataset_parses():
    lines = [ln for ln in DATASET.read_text(encoding="utf-8").splitlines() if ln.strip()]
    cases = [Case(**json.loads(ln)) for ln in lines]
    assert cases and all(case.question for case in cases)


class TestRankMetrics:
    def test_a_perfect_ranking_scores_top_marks_where_it_should(self):
        scores = score_retrieval(["a", "b"], ["a"])
        assert scores["hit"] == 1.0
        assert scores["mrr"] == 1.0
        assert scores["recall"] == 1.0
        # Precision is halved by the irrelevant second result, correctly.
        assert scores["precision"] == 0.5
        assert scores["ndcg"] == 1.0

    def test_nothing_relevant_scores_zero_across_the_board(self):
        scores = score_retrieval(["x", "y"], ["a"])
        assert set(scores.values()) == {0.0}

    def test_reciprocal_rank_reflects_position(self):
        assert score_retrieval(["x", "a"], ["a"])["mrr"] == 0.5

    def test_ndcg_rewards_ranking_the_right_document_higher(self):
        # The distinction the ranked metrics exist to make: same documents
        # retrieved, different order.
        first = score_retrieval(["a", "x", "y"], ["a"])["ndcg"]
        last = score_retrieval(["x", "y", "a"], ["a"])["ndcg"]
        assert first > last

    def test_recall_counts_how_many_of_the_wanted_documents_were_found(self):
        assert score_retrieval(["a"], ["a", "b"])["recall"] == 0.5
        assert score_retrieval(["a", "b"], ["a", "b"])["recall"] == 1.0

    def test_an_unlabelled_case_scores_nothing_rather_than_something(self):
        # A case with no expected documents cannot be scored for ranking, and
        # inventing a number would quietly flatter every mode equally.
        assert set(score_retrieval(["a"], []).values()) == {0.0}


class TestGroundingMetrics:
    def test_a_marker_with_no_citation_behind_it_is_invalid(self):
        # A fabricated marker is worse than a missing one: it looks like
        # evidence.
        assert citations_are_valid("As stated [3].", [Citation("[1]")]) == 0.0

    def test_markers_that_all_map_are_valid(self):
        assert citations_are_valid("As stated [1][2].", [Citation("[1]"), Citation("[2]")]) == 1.0

    def test_an_answer_with_no_markers_is_not_penalised(self):
        assert citations_are_valid("I could not find that.", []) == 1.0

    def test_groundedness_is_higher_when_the_answer_uses_the_passages(self):
        chunks = [Chunk("the shaft width is 1600 mm and the pit depth is 1200 mm")]
        grounded = groundedness("the shaft width is 1600 mm", chunks)
        invented = groundedness("the warranty covers marine propulsion systems", chunks)
        assert grounded > invented

    def test_groundedness_of_an_empty_answer_is_zero(self):
        assert groundedness("", [Chunk("anything")]) == 0.0


class TestSummary:
    def test_absent_metrics_are_reported_as_absent_not_as_zero(self):
        from scripts.evaluate import Scores

        summary = summarise([Scores(hit=1.0, latency_ms=10.0)], top_k=5)
        # Groundedness needs generation, which a retrieval-only run skips.
        assert summary["grounded"] is None
        assert summary["hit@5"] == 1.0

    def test_latency_percentiles_are_ordered(self):
        from scripts.evaluate import Scores

        summary = summarise([Scores(latency_ms=float(i)) for i in range(100)], top_k=5)
        assert summary["latency_p50_ms"] <= summary["latency_p95_ms"]
        assert summary["latency_p95_ms"] <= summary["latency_p99_ms"]

    def test_every_retrieval_mode_is_comparable(self):
        assert set(MODES) == {"dense", "sparse", "hybrid", "hybrid+rerank"}
