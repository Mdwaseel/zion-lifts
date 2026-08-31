"""Quality benchmarks. Marked so they stay out of the default run: pytest -m evaluation"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.evaluate import Case, score_retrieval

DATASET = Path(__file__).parent / "dataset.jsonl"

pytestmark = pytest.mark.evaluation


def test_dataset_parses():
    lines = [ln for ln in DATASET.read_text(encoding="utf-8").splitlines() if ln.strip()]
    cases = [Case(**json.loads(ln)) for ln in lines]
    assert cases and all(case.question for case in cases)


def test_scoring_is_correct_for_a_perfect_ranking():
    hit, rr, precision = score_retrieval(["a", "b"], ["a"])
    assert (hit, rr) == (1.0, 1.0)
    assert precision == 0.5


def test_scoring_is_zero_when_nothing_relevant_is_retrieved():
    assert score_retrieval(["x", "y"], ["a"]) == (0.0, 0.0, 0.0)


def test_reciprocal_rank_reflects_position():
    _, rr, _ = score_retrieval(["x", "a"], ["a"])
    assert rr == 0.5
