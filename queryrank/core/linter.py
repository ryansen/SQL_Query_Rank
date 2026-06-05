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
    suggestion: str = ""


def _check_select_star(sql: str) -> list[LintWarning]:
    if re.search(r"\bSELECT\s+\*", sql, re.IGNORECASE):
        return [LintWarning(
            "L001",
            "Avoid SELECT *; it can read and return more data than the task needs.",
            Severity.WARNING,
            "Select only the output columns required by the prompt.",
        )]
    return []


def _check_cross_join(sql: str) -> list[LintWarning]:
    if re.search(r"\bCROSS\s+JOIN\b", sql, re.IGNORECASE):
        return [LintWarning(
            "L002",
            "CROSS JOIN detected; it multiplies rows and can explode runtime.",
            Severity.WARNING,
            "Use an INNER JOIN with an ON condition unless every pair of rows is required.",
        )]
    return []


def _check_unnecessary_distinct(sql: str) -> list[LintWarning]:
    if re.search(r"\bSELECT\s+DISTINCT\b", sql, re.IGNORECASE):
        return [LintWarning(
            "L003",
            "SELECT DISTINCT can hide duplicate rows caused by a join and force de-duplication.",
            Severity.INFO,
            "Check whether the join condition is specific enough before using DISTINCT.",
        )]
    return []


def _check_order_without_limit(sql: str) -> list[LintWarning]:
    has_order = bool(re.search(r"\bORDER\s+BY\b", sql, re.IGNORECASE))
    has_limit = bool(re.search(r"\bLIMIT\b", sql, re.IGNORECASE))
    if has_order and not has_limit:
        return [LintWarning(
            "L004",
            "ORDER BY without LIMIT sorts the full result set.",
            Severity.INFO,
            "Keep it when the prompt requires ordered output; otherwise remove it.",
        )]
    return []


def _check_repeated_subqueries(sql: str) -> list[LintWarning]:
    subqueries = re.findall(r"\(\s*SELECT\b[^)]+\)", sql, re.IGNORECASE | re.DOTALL)
    seen: dict[str, int] = {}
    for sq in subqueries:
        key = re.sub(r"\s+", " ", sq.strip().lower())
        seen[key] = seen.get(key, 0) + 1
    if any(count > 1 for count in seen.values()):
        return [LintWarning(
            "L005",
            "Repeated subquery detected; the database may do the same work more than once.",
            Severity.WARNING,
            "Compute it once in a CTE or derived table and reuse the result.",
        )]
    return []


def _check_function_on_column(sql: str) -> list[LintWarning]:
    pattern = r"\bWHERE\b[^;]*\b(LOWER|UPPER|DATE|YEAR|MONTH|TO_CHAR|SUBSTR|CAST)\s*\("
    if re.search(pattern, sql, re.IGNORECASE):
        return [LintWarning(
            "L006",
            "Function applied to a column in WHERE; this can prevent normal index use.",
            Severity.WARNING,
            "Rewrite as a range predicate when possible, such as order_date >= ... AND order_date < ...",
        )]
    return []


def _check_missing_join_condition(sql: str) -> list[LintWarning]:
    from_clause = re.search(
        r"\bFROM\b(.+?)(?:\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|$)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if not from_clause:
        return []
    tables = [t.strip() for t in from_clause.group(1).split(",") if t.strip()]
    if len(tables) > 1 and not re.search(r"\bJOIN\b", sql, re.IGNORECASE):
        return [LintWarning(
            "L007",
            "Comma-separated tables without explicit JOIN; possible Cartesian product.",
            Severity.WARNING,
            "Use explicit JOIN ... ON ... so the row-matching condition is obvious.",
        )]
    return []


def _check_excessive_nesting(sql: str) -> list[LintWarning]:
    depth = 0
    max_depth = 0
    for ch in sql:
        if ch == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ")":
            depth = max(depth - 1, 0)
    if max_depth >= 4:
        return [LintWarning(
            "L008",
            f"Query has {max_depth} levels of nesting.",
            Severity.INFO,
            "Consider flattening with a CTE or moving filters closer to the base tables.",
        )]
    return []


def _check_or_in_where(sql: str) -> list[LintWarning]:
    where_clause = re.search(
        r"\bWHERE\b(.+?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if where_clause and re.search(r"\bOR\b", where_clause.group(1), re.IGNORECASE):
        return [LintWarning(
            "L009",
            "OR in WHERE can make index usage less selective, especially across different columns.",
            Severity.INFO,
            "If each branch is selective, compare against a UNION ALL version and benchmark both.",
        )]
    return []


def _check_leading_wildcard_like(sql: str) -> list[LintWarning]:
    if re.search(r"\b(?:LIKE|ILIKE)\s+['\"]%", sql, re.IGNORECASE):
        return [LintWarning(
            "L010",
            "Leading-wildcard LIKE/ILIKE cannot use a normal b-tree index efficiently.",
            Severity.WARNING,
            "Prefer prefix searches, a trigram index, or full-text search for contains matching.",
        )]
    return []


def _check_not_in(sql: str) -> list[LintWarning]:
    if re.search(r"\bNOT\s+IN\s*\(", sql, re.IGNORECASE):
        return [LintWarning(
            "L011",
            "NOT IN can be slow and has tricky NULL behavior.",
            Severity.INFO,
            "Consider NOT EXISTS with a correlated condition when excluding matching rows.",
        )]
    return []


def _check_offset(sql: str) -> list[LintWarning]:
    if re.search(r"\bOFFSET\s+\d+", sql, re.IGNORECASE):
        return [LintWarning(
            "L012",
            "OFFSET makes the database scan and discard skipped rows.",
            Severity.INFO,
            "For deep pagination, use keyset pagination with a WHERE condition on the last seen value.",
        )]
    return []


def _check_union(sql: str) -> list[LintWarning]:
    if re.search(r"\bUNION\b(?!\s+ALL\b)", sql, re.IGNORECASE):
        return [LintWarning(
            "L013",
            "UNION removes duplicates, which usually requires sorting or hashing all rows.",
            Severity.INFO,
            "Use UNION ALL if duplicate removal is not required.",
        )]
    return []


def _check_limit_without_order(sql: str) -> list[LintWarning]:
    has_limit = bool(re.search(r"\bLIMIT\b", sql, re.IGNORECASE))
    has_order = bool(re.search(r"\bORDER\s+BY\b", sql, re.IGNORECASE))
    if has_limit and not has_order:
        return [LintWarning(
            "L014",
            "LIMIT without ORDER BY can return arbitrary rows.",
            Severity.INFO,
            "Add ORDER BY when the prompt asks for top, latest, earliest, or ranked results.",
        )]
    return []


def _check_correlated_subquery(sql: str) -> list[LintWarning]:
    if re.search(r"\bWHERE\b.+\b(?:IN|EXISTS)\s*\(\s*SELECT\b", sql, re.IGNORECASE | re.DOTALL):
        return [LintWarning(
            "L015",
            "Subquery in WHERE may be correlated or repeatedly evaluated depending on the plan.",
            Severity.INFO,
            "Compare against a JOIN or pre-aggregated CTE version if the benchmark is slow.",
        )]
    return []


_CHECKS = [
    _check_select_star,
    _check_cross_join,
    _check_unnecessary_distinct,
    _check_order_without_limit,
    _check_repeated_subqueries,
    _check_function_on_column,
    _check_missing_join_condition,
    _check_excessive_nesting,
    _check_or_in_where,
    _check_leading_wildcard_like,
    _check_not_in,
    _check_offset,
    _check_union,
    _check_limit_without_order,
    _check_correlated_subquery,
]

MAX_LINT_SCORE = 10


def lint_query(sql: str) -> list[LintWarning]:
    """Run all lint checks and return a list of warnings."""
    sql = _strip_sql_comments(sql)
    warnings: list[LintWarning] = []
    for check in _CHECKS:
        warnings.extend(check(sql))
    return warnings


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
    return sql


def lint_score(warnings: list[LintWarning]) -> float:
    """Compute 0-10 lint score: -2 per WARNING, -1 per INFO, floor 0."""
    deductions = sum(2 if w.severity == Severity.WARNING else 1 for w in warnings)
    return max(float(MAX_LINT_SCORE - deductions), 0.0)
