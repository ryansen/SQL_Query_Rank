"""Evaluate commands: submit, explain, benchmark."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from queryrank.core.db import get_connection, drop_schema
from queryrank.core.questions import get_question
from queryrank.core.profile import UserProfile
from queryrank.core.executor import compare_against_references, run_query, run_sql_file
from queryrank.core.explain import explain_query
from queryrank.core.benchmark import benchmark_query, benchmark_references
from queryrank.core.linter import lint_query, lint_score
from queryrank.core.scoring import QueryScore, rank_solutions
from queryrank.core import reporter

app = typer.Typer(help="Submit and evaluate SQL answers.")
console = Console()


# ------------------------------------------------------------------
# submit
# ------------------------------------------------------------------

@app.command()
def submit(
    question_id: str = typer.Argument(..., help="Question ID"),
    answer_file: Path = typer.Argument(..., help="Path to your answer.sql"),
    size: str = typer.Option("medium", "--size", "-s", help="Dataset size: small | medium | large"),
    runs: int = typer.Option(5, "--runs", "-r", help="Benchmark iterations"),
) -> None:
    """
    Submit your SQL answer for evaluation.

    Provisions a fresh DB, runs correctness checks, benchmarks, EXPLAIN ANALYZE,
    linting, and prints a scored report.
    """
    _require_profile()
    q = _require_question(question_id)
    user_sql = _read_sql(answer_file)

    console.print(f"\n[bold cyan]Evaluating[/] [bold]{q.config.title}[/]…\n")

    with get_connection() as conn:
        # 1. Fresh schema + data
        with conn.transaction():
            drop_schema(conn)
            q.setup_schema(conn)
            q.generate_data(conn, size=size)

        # 2. Correctness check
        is_correct, reason, user_rows = compare_against_references(
            conn, user_sql, q.references
        )
        reporter.print_correctness(is_correct, reason)

        # 3. Benchmark user query
        user_bench = benchmark_query(conn, user_sql, runs=runs)

        # 4. Benchmark reference queries
        ref_sqls = {p.stem: p.read_text() for p in q.references}
        ref_benches = benchmark_references(conn, ref_sqls, runs=runs)

        # 5. Best reference median
        best_ref = min(ref_benches.values(), key=lambda b: b.median_ms, default=None)

        # 6. EXPLAIN ANALYZE
        plan = explain_query(conn, user_sql)

        # 7. Lint
        warnings = lint_query(user_sql)

    # 8. Score
    score = QueryScore(
        is_correct=is_correct,
        user_benchmark=user_bench,
        best_ref_benchmark=best_ref,
        plan_features=plan,
        lint_warnings=warnings,
    ).compute()

    # 9. Rank
    ref_medians = {label: b.median_ms for label, b in ref_benches.items()}
    score.rank, score.total_solutions = rank_solutions(user_bench.median_ms, ref_medians)

    # 10. Report
    reporter.print_benchmark_table(user_bench.median_ms, ref_medians, score.rank, score.total_solutions)
    reporter.print_plan_summary(plan)
    reporter.print_lint_warnings(warnings)
    reporter.print_score_card(score)

    # 11. Persist to profile
    profile = UserProfile.load()
    if profile:
        profile.record_attempt(question_id, score.total, is_correct)


# ------------------------------------------------------------------
# explain
# ------------------------------------------------------------------

@app.command()
def explain(
    question_id: str = typer.Argument(..., help="Question ID"),
    answer_file: Path = typer.Argument(..., help="Path to your answer.sql"),
    size: str = typer.Option("medium", "--size", "-s", help="Dataset size"),
    raw: bool = typer.Option(False, "--raw", help="Print the full JSON plan"),
) -> None:
    """Run EXPLAIN ANALYZE on your query and show the plan analysis."""
    q = _require_question(question_id)
    user_sql = _read_sql(answer_file)

    with get_connection() as conn:
        with conn.transaction():
            drop_schema(conn)
            q.setup_schema(conn)
            q.generate_data(conn, size=size)

        plan = explain_query(conn, user_sql)

    reporter.print_plan_summary(plan)
    if raw:
        reporter.print_explain_json(plan)


# ------------------------------------------------------------------
# benchmark
# ------------------------------------------------------------------

@app.command()
def benchmark(
    question_id: str = typer.Argument(..., help="Question ID"),
    answer_file: Path = typer.Argument(..., help="Path to your answer.sql"),
    size: str = typer.Option("medium", "--size", "-s", help="Dataset size"),
    runs: int = typer.Option(10, "--runs", "-r", help="Benchmark iterations"),
) -> None:
    """Benchmark your query against reference solutions."""
    q = _require_question(question_id)
    user_sql = _read_sql(answer_file)

    with get_connection() as conn:
        with conn.transaction():
            drop_schema(conn)
            q.setup_schema(conn)
            q.generate_data(conn, size=size)

        user_bench = benchmark_query(conn, user_sql, runs=runs)
        ref_sqls = {p.stem: p.read_text() for p in q.references}
        ref_benches = benchmark_references(conn, ref_sqls, runs=runs)

    ref_medians = {label: b.median_ms for label, b in ref_benches.items()}
    rank, total = rank_solutions(user_bench.median_ms, ref_medians)
    reporter.print_benchmark_table(user_bench.median_ms, ref_medians, rank, total)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _require_profile() -> UserProfile:
    p = UserProfile.load()
    if not p:
        console.print("[yellow]No profile.[/] Run [cyan]queryrank login[/] first.")
        raise typer.Exit(1)
    return p


def _require_question(question_id: str):  # type: ignore[return]
    q = get_question(question_id)
    if not q:
        console.print(f"[red]Question '{question_id}' not found.[/]")
        raise typer.Exit(1)
    return q


def _read_sql(path: Path) -> str:
    if not path.exists():
        console.print(f"[red]File not found:[/] {path}")
        raise typer.Exit(1)
    return path.read_text().strip()
