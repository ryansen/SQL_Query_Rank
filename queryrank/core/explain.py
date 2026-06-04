"""EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) parser for QueryRank."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import psycopg


@dataclass
class PlanFeatures:
    """Extracted features from a query plan."""
    planning_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    total_cost: float = 0.0

    # Node types detected
    seq_scans: int = 0
    index_scans: int = 0
    index_only_scans: int = 0
    hash_joins: int = 0
    merge_joins: int = 0
    nested_loops: int = 0
    sorts: int = 0
    aggregates: int = 0

    # Danger signals
    temp_disk_usage: bool = False
    rows_removed_by_filter: int = 0

    # Raw plan for display
    raw_plan: list[dict[str, Any]] = field(default_factory=list)

    @property
    def plan_score(self) -> float:
        """
        0-15 quality score based on plan features.
        Penalises seq scans, temp disk, excessive sorts.
        """
        score = 15.0
        score -= min(self.seq_scans * 3, 9)          # −3 per seq scan, cap at −9
        score -= 5 if self.temp_disk_usage else 0
        score -= min(self.sorts * 1, 3)               # −1 per sort, cap at −3
        score -= min(self.nested_loops * 0.5, 2)
        return max(score, 0.0)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Planning: {self.planning_time_ms:.1f} ms   "
            f"Execution: {self.execution_time_ms:.1f} ms",
            f"Seq scans: {self.seq_scans}   "
            f"Index scans: {self.index_scans}   "
            f"Index-only: {self.index_only_scans}",
            f"Hash joins: {self.hash_joins}   "
            f"Merge joins: {self.merge_joins}   "
            f"Nested loops: {self.nested_loops}",
            f"Sorts: {self.sorts}   Aggregates: {self.aggregates}   "
            f"Temp disk: {'YES ⚠' if self.temp_disk_usage else 'no'}",
        ]
        return lines


# ------------------------------------------------------------------

def explain_query(conn: psycopg.Connection, sql: str) -> PlanFeatures:
    """Run EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) and parse the result."""
    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
    with conn.cursor() as cur:
        cur.execute(explain_sql)
        row = cur.fetchone()

    raw: list[dict[str, Any]] = row[0]  # psycopg returns the JSON already decoded
    top = raw[0] if raw else {}

    features = PlanFeatures(
        planning_time_ms=top.get("Planning Time", 0.0),
        execution_time_ms=top.get("Execution Time", 0.0),
        raw_plan=raw,
    )

    if "Plan" in top:
        _walk_plan(top["Plan"], features)
        features.total_cost = top["Plan"].get("Total Cost", 0.0)

    return features


def _walk_plan(node: dict[str, Any], features: PlanFeatures) -> None:
    """Recursively walk plan nodes and accumulate feature counts."""
    node_type: str = node.get("Node Type", "")

    match node_type:
        case "Seq Scan":
            features.seq_scans += 1
            features.rows_removed_by_filter += node.get("Rows Removed by Filter", 0)
        case "Index Scan":
            features.index_scans += 1
        case "Index Only Scan":
            features.index_only_scans += 1
        case "Hash Join":
            features.hash_joins += 1
        case "Merge Join":
            features.merge_joins += 1
        case "Nested Loop":
            features.nested_loops += 1
        case "Sort":
            features.sorts += 1
        case s if "Aggregate" in s:
            features.aggregates += 1

    if node.get("Temp Written Blocks", 0) > 0:
        features.temp_disk_usage = True

    for child in node.get("Plans", []):
        _walk_plan(child, features)
