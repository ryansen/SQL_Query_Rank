"""Query benchmarking for QueryRank."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable

import psycopg


@dataclass
class BenchmarkResult:
    runs: int
    times_ms: list[float]

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.times_ms)

    @property
    def median_ms(self) -> float:
        return statistics.median(self.times_ms)

    @property
    def min_ms(self) -> float:
        return min(self.times_ms)

    @property
    def max_ms(self) -> float:
        return max(self.times_ms)

    @property
    def stdev_ms(self) -> float:
        return statistics.stdev(self.times_ms) if len(self.times_ms) > 1 else 0.0


def benchmark_query(
    conn: psycopg.Connection,
    sql: str,
    runs: int = 5,
) -> BenchmarkResult:
    """Run a query `runs` times and collect wall-clock times in ms."""
    times: list[float] = []

    for _ in range(runs):
        # Use a savepoint so we can rollback any side-effects each run
        with conn.transaction():
            start = time.perf_counter()
            conn.execute(sql)
            elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult(runs=runs, times_ms=times)


def runtime_score(user_median_ms: float, best_ref_median_ms: float) -> float:
    """
    25-point score comparing user query median time to the best reference.

    Full 25 pts if user is within 110% of best reference.
    Scales down to 0 at 5× slower.
    """
    if best_ref_median_ms <= 0:
        return 25.0

    ratio = user_median_ms / best_ref_median_ms  # 1.0 = same speed

    if ratio <= 1.10:
        return 25.0
    if ratio >= 5.0:
        return 0.0

    # Linear interpolation between 1.10 and 5.0
    return round(25.0 * (5.0 - ratio) / (5.0 - 1.10), 1)


def benchmark_references(
    conn: psycopg.Connection,
    ref_sqls: dict[str, str],   # {label: sql}
    runs: int = 5,
) -> dict[str, BenchmarkResult]:
    return {label: benchmark_query(conn, sql, runs=runs) for label, sql in ref_sqls.items()}
