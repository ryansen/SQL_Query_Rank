"""SQL lint checks for QueryRank."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintWarning:
    code: str
    message: str
    severity: Severity = Severity.WARNING


# ------------------------------------------------------------------
# Individual checks (each returns a LintWarning or None)
# ------------------------------------------------------------------

def _check_select_star(sql: str) -> list[LintWarning]:
    if re.search(r"\bSELECT\s+\*", sql, re.IGNORECASE):
        return [LintWarning("L001", "Avoid SELECT *; list columns explicitly.", Severity.WARNING)]
    return []


def _check_cross_join(sql: str) -> list[LintWarning]:
    if re.search(r"\bCROSS\s+JOIN\b", sql, re.IGNORECASE):
        return [LintWarning("L002", "CROSS JOIN detected — ensure this is intentional.", Severity.WARNING)]
    return []


def _check_unnecessary_distinct(sql: str) -> list[LintWarning]:
    # Heuristic: DISTINCT inside a subquery is often unnecessary
    if re.search(r"\bSELECT\s+DISTINCT\b", sql, re.IGNORECASE):
        return [LintWarning("L003", "SELECT DISTINCT may indicate a missing join condition.", Severity.INFO)]
    return []


def _check_order_without_limit(sql: str) -> list[LintWarning]:
    has_order = bool(re.search(r"\bORDER\s+BY\b", sql, re.IGNORECASE))
    has_limit = bool(re.search(r"\bLIMIT\b", sql, re.IGNORECASE))
    if has_order and not has_limit:
        return [LintWarning("L004", "ORDER BY without LIMIT may be unnecessary and costly.", Severity.INFO)]
    return []


def _check_repeated_subqueries(sql: str) -> list[LintWarning]:
    # Simple heuristic: same FROM (...) block appears more than once
    subqueries = re.findall(r"\(\s*SELECT\b[^)]+\)", sql, re.IGNORECASE | re.DOTALL)
    seen: dict[str, int] = {}
    for sq in subqueries:
        key = re.sub(r"\s+", " ", sq.strip().lower())
        seen[key] = seen.get(key, 0) + 1
    repeated = [k for k, v in seen.items() if v > 1]
    if repeated:
        return [LintWarning("L005", "Repeated subquery detected — consider a CTE.", Severity.WARNING)]
    return []


def _check_function_on_column(sql: str) -> list[LintWarning]:
    # Warn if a function is wrapped around a likely-indexed column in a WHERE
    pattern = r"\bWHERE\b[^;]*\b(LOWER|UPPER|DATE|YEAR|MONTH|TO_CHAR|SUBSTR|CAST)\s*\("
    if re.search(pattern, sql, re.IGNORECASE):
        return [LintWarning(
            "L006",
            "Function applied to column in WHERE — may prevent index use.",
            Severity.WARNING,
        )]
    return []


def _check_missing_join_condition(sql: str) -> list[LintWarning]:
    # Detect "FROM a, b" implicit cross join without a WHERE join condition
    from_clause = re.search(r"\bFROM\b(.+?)(?:\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|$)", sql, re.IGNORECASE | re.DOTALL)
    if from_clause:
        tables = [t.strip() for t in from_clause.group(1).split(",") if t.strip()]
        if len(tables) > 1 and not re.search(r"\bJOIN\b", sql, re.IGNORECASE):
            return [LintWarning("L007", "Comma-separated tables without JOIN — possible Cartesian product.", Severity.WARNING)]
    return []


def _check_excessive_nesting(sql: str) -> list[LintWarning]:
    depth = 0
    max_depth = 0
    for ch in sql:
        if ch == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ")":
            depth -= 1
    if max_depth >= 4:
        return [LintWarning("L008", f"Query has {max_depth} levels of nesting — consider simplifying.", Severity.INFO)]
    return []


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------

_CHECKS = [
    _check_select_star,
    _check_cross_join,
    _check_unnecessary_distinct,
    _check_order_without_limit,
    _check_repeated_subqueries,
    _check_function_on_column,
    _check_missing_join_condition,
    _check_excessive_nesting,
]

MAX_LINT_SCORE = 10


def lint_query(sql: str) -> list[LintWarning]:
    """Run all lint checks and return a list of warnings."""
    warnings: list[LintWarning] = []
    for check in _CHECKS:
        warnings.extend(check(sql))
    return warnings


def lint_score(warnings: list[LintWarning]) -> float:
    """Compute 0-10 lint score: -2 per WARNING, -1 per INFO, floor 0."""
    deductions = sum(
        2 if w.severity == Severity.WARNING else 1
        for w in warnings
    )
    return max(float(MAX_LINT_SCORE - deductions), 0.0)
