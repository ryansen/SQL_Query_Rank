"""EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) parser for QueryRank."""

from __future__ import annotations

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
    temp_written_blocks: int = 0
    shared_read_blocks: int = 0
    shared_hit_blocks: int = 0
    rows_removed_by_filter: int = 0
    seq_scan_tables: list[str] = field(default_factory=list)
    large_filter_nodes: list[str] = field(default_factory=list)
    sort_methods: list[str] = field(default_factory=list)
    estimate_mismatches: list[str] = field(default_factory=list)

    # Raw plan for display
    raw_plan: list[dict[str, Any]] = field(default_factory=list)

    @property
    def plan_score(self) -> float:
        """0-15 quality score based on plan features."""
        score = 15.0
        score -= min(self.seq_scans * 3, 9)
        score -= 5 if self.temp_disk_usage else 0
        score -= min(self.sorts * 1, 3)
        score -= min(self.nested_loops * 0.5, 2)
        return max(score, 0.0)

    def summary_lines(self) -> list[str]:
        return [
            f"Planning: {self.planning_time_ms:.1f} ms   "
            f"Execution: {self.execution_time_ms:.1f} ms",
            f"Seq scans: {self.seq_scans}   "
            f"Index scans: {self.index_scans}   "
            f"Index-only: {self.index_only_scans}",
            f"Hash joins: {self.hash_joins}   "
            f"Merge joins: {self.merge_joins}   "
            f"Nested loops: {self.nested_loops}",
            f"Sorts: {self.sorts}   Aggregates: {self.aggregates}   "
            f"Temp disk: {'YES' if self.temp_disk_usage else 'no'}",
            f"Rows removed by filters: {self.rows_removed_by_filter}   "
            f"Shared reads: {self.shared_read_blocks} blocks",
        ]

    def analysis_lines(self) -> list[str]:
        """Return human-readable performance observations from the plan."""
        lines: list[str] = []

        if self.seq_scan_tables:
            tables = ", ".join(sorted(set(self.seq_scan_tables)))
            lines.append(
                f"Sequential scan on {tables}: fine for tiny tables, but slow on large datasets "
                "when a selective filter or join could use an index."
            )

        if self.rows_removed_by_filter >= 1_000:
            lines.append(
                f"Filters discarded {self.rows_removed_by_filter:,} rows after reading them. "
                "Try pushing filters earlier or using predicates that match indexed columns."
            )

        if self.sorts:
            detail = f" Methods: {', '.join(self.sort_methods)}." if self.sort_methods else ""
            lines.append(
                f"{self.sorts} sort step(s) found. Sorts are often necessary for ORDER BY, "
                f"GROUP BY, DISTINCT, and merge joins, but they can dominate runtime on large outputs.{detail}"
            )

        if self.temp_disk_usage:
            lines.append(
                f"The plan wrote temporary data to disk ({self.temp_written_blocks} blocks). "
                "That usually means a sort/hash step outgrew memory and became much slower."
            )

        if self.nested_loops and self.seq_scans:
            lines.append(
                "Nested loop plus sequential scan can mean repeated table scans. "
                "Check join keys and indexes, or pre-aggregate before joining."
            )

        if self.shared_read_blocks >= 1_000:
            lines.append(
                f"The plan read {self.shared_read_blocks:,} shared blocks. "
                "Reducing scanned rows is likely to help more than rewriting SELECT expressions."
            )

        lines.extend(self.estimate_mismatches[:3])

        if not lines:
            lines.append(
                "No obvious plan red flags. If runtime is still slow, compare the raw plan with "
                "the fastest reference and look for different join order, filtering, or sorting."
            )

        return lines


def explain_query(conn: psycopg.Connection, sql: str) -> PlanFeatures:
    """Run EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) and parse the result."""
    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
    with conn.cursor() as cur:
        cur.execute(explain_sql)
        row = cur.fetchone()

    raw: list[dict[str, Any]] = row[0]
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
    relation = node.get("Relation Name", "")
    actual_rows = float(node.get("Actual Rows", 0) or 0)
    plan_rows = float(node.get("Plan Rows", 0) or 0)

    match node_type:
        case "Seq Scan":
            features.seq_scans += 1
            if relation:
                features.seq_scan_tables.append(str(relation))
            features.rows_removed_by_filter += int(node.get("Rows Removed by Filter", 0) or 0)
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

    removed = int(node.get("Rows Removed by Filter", 0) or 0)
    if removed >= 1_000:
        label = node_type
        if relation:
            label += f" on {relation}"
        features.large_filter_nodes.append(f"{label} removed {removed:,} rows")

    if node_type == "Sort":
        method = node.get("Sort Method")
        space_type = node.get("Sort Space Type")
        space_used = node.get("Sort Space Used")
        if method:
            suffix = f" ({space_used}kB {space_type})" if space_type and space_used else ""
            features.sort_methods.append(f"{method}{suffix}")

    temp_written = int(node.get("Temp Written Blocks", 0) or 0)
    if temp_written > 0:
        features.temp_disk_usage = True
        features.temp_written_blocks += temp_written

    features.shared_read_blocks += int(node.get("Shared Read Blocks", 0) or 0)
    features.shared_hit_blocks += int(node.get("Shared Hit Blocks", 0) or 0)

    if plan_rows > 0 and actual_rows > 0:
        ratio = max(actual_rows / plan_rows, plan_rows / actual_rows)
        if ratio >= 10:
            label = node_type
            if relation:
                label += f" on {relation}"
            features.estimate_mismatches.append(
                f"Planner row estimate was off by about {ratio:.0f}x at {label}. "
                "Bad estimates can lead to poor join order or join method choices."
            )

    for child in node.get("Plans", []):
        _walk_plan(child, features)
