"""Scoring and ranking for QueryRank."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from queryrank.core.benchmark import BenchmarkResult, runtime_score
from queryrank.core.explain import PlanFeatures
from queryrank.core.linter import LintWarning, lint_score


# Weights (must sum to 100)
WEIGHT_CORRECTNESS = 50
WEIGHT_RUNTIME = 25
WEIGHT_PLAN = 15
WEIGHT_LINT = 10


@dataclass
class QueryScore:
    # Raw inputs
    is_correct: bool
    user_benchmark: BenchmarkResult
    best_ref_benchmark: Optional[BenchmarkResult]
    plan_features: PlanFeatures
    lint_warnings: list[LintWarning]

    # Computed sub-scores (set by compute())
    correctness_score: float = 0.0
    runtime_score_val: float = 0.0
    plan_score: float = 0.0
    lint_score_val: float = 0.0
    total: float = 0.0

    # Rank among solutions (set externally)
    rank: int = 0
    total_solutions: int = 0   # includes references + user

    def compute(self) -> "QueryScore":
        self.correctness_score = float(WEIGHT_CORRECTNESS) if self.is_correct else 0.0

        if self.is_correct:
            best_ms = self.best_ref_benchmark.median_ms if self.best_ref_benchmark else 0
            self.runtime_score_val = runtime_score(self.user_benchmark.median_ms, best_ms)
            self.plan_score = self.plan_features.plan_score
            self.lint_score_val = lint_score(self.lint_warnings)
        # If incorrect, sub-scores stay 0

        self.total = (
            self.correctness_score
            + self.runtime_score_val
            + self.plan_score
            + self.lint_score_val
        )
        return self

    @property
    def grade(self) -> str:
        if self.total >= 90:
            return "S"
        if self.total >= 75:
            return "A"
        if self.total >= 60:
            return "B"
        if self.total >= 45:
            return "C"
        if self.total >= 30:
            return "D"
        return "F"

    @property
    def grade_color(self) -> str:
        return {
            "S": "bold magenta",
            "A": "bold green",
            "B": "green",
            "C": "yellow",
            "D": "red",
            "F": "bold red",
        }.get(self.grade, "white")


def rank_solutions(
    user_median_ms: float,
    ref_medians: dict[str, float],
) -> tuple[int, int]:
    """
    Rank user among reference solutions by median runtime.
    Returns (rank, total_solutions).  1 = fastest.
    """
    all_times = list(ref_medians.values()) + [user_median_ms]
    all_times.sort()
    rank = all_times.index(user_median_ms) + 1
    return rank, len(all_times)
