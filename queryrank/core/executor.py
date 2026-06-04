"""Query execution and correctness comparison for QueryRank."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


# ------------------------------------------------------------------
# Execution
# ------------------------------------------------------------------

def run_query(conn: psycopg.Connection, sql: str) -> list[dict[str, Any]]:
    """Execute a SELECT query and return rows as a list of dicts."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchall()


def run_sql_file(conn: psycopg.Connection, path: Path) -> list[dict[str, Any]]:
    """Run a .sql file and return its rows."""
    return run_query(conn, path.read_text())


# ------------------------------------------------------------------
# Correctness
# ------------------------------------------------------------------

def normalise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort rows by their string representation for order-insensitive comparison."""
    return sorted(rows, key=lambda r: str(sorted(r.items())))


def rows_equal(
    user_rows: list[dict[str, Any]],
    ref_rows: list[dict[str, Any]],
    ordered: bool = False,
) -> tuple[bool, str]:
    """
    Compare two result sets.

    Returns (is_correct, reason_string).
    """
    if len(user_rows) != len(ref_rows):
        return (
            False,
            f"Row count mismatch: got {len(user_rows)}, expected {len(ref_rows)}",
        )

    if not ordered:
        user_rows = normalise(user_rows)
        ref_rows = normalise(ref_rows)

    for i, (u, r) in enumerate(zip(user_rows, ref_rows)):
        # Coerce values to strings for comparison (handles Decimal vs float etc.)
        u_str = {k: str(v) for k, v in u.items()}
        r_str = {k: str(v) for k, v in r.items()}
        if u_str != r_str:
            return False, f"Row {i} differs: got {u_str}, expected {r_str}"

    return True, "Results match"


def compare_against_references(
    conn: psycopg.Connection,
    user_sql: str,
    ref_paths: list[Path],
    ordered: bool = False,
) -> tuple[bool, str, list[dict[str, Any]]]:
    """
    Run user query and all references.  User is correct if it matches ANY reference.

    Returns (is_correct, reason, user_rows).
    """
    user_rows = run_query(conn, user_sql)

    last_reason = "No reference solutions found"
    for ref_path in ref_paths:
        ref_rows = run_sql_file(conn, ref_path)
        ok, reason = rows_equal(user_rows, ref_rows, ordered=ordered)
        if ok:
            return True, reason, user_rows
        last_reason = reason

    return False, last_reason, user_rows
