"""Rich terminal report renderer for QueryRank."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box

from queryrank.core.explain import PlanFeatures
from queryrank.core.linter import LintWarning, Severity
from queryrank.core.scoring import QueryScore

console = Console()


def print_question_header(title: str, difficulty: str, tags: list[str]) -> None:
    color = {"easy": "green", "medium": "yellow", "hard": "red"}.get(difficulty, "white")
    tag_str = "  ".join(f"[dim]#{t}[/]" for t in tags)
    console.print(
        Panel(
            f"[bold]{title}[/]\n"
            f"[{color}]{difficulty.upper()}[/]  {tag_str}",
            title="[bold cyan]QueryRank Challenge[/]",
            border_style="cyan",
        )
    )


def print_prompt(prompt: str) -> None:
    console.print(Panel(prompt.strip(), title="[bold]Prompt[/]", border_style="dim"))


def print_correctness(is_correct: bool, reason: str) -> None:
    if is_correct:
        console.print(f"[bold green]✓  Correct![/]  {reason}")
    else:
        console.print(f"[bold red]✗  Incorrect.[/]  {reason}")


def print_benchmark_table(
    user_median_ms: float,
    ref_medians: dict[str, float],
    rank: int,
    total: int,
) -> None:
    table = Table(title="Benchmark Results", box=box.ROUNDED, show_lines=True)
    table.add_column("Solution", style="cyan")
    table.add_column("Median (ms)", justify="right")
    table.add_column("", justify="center")

    all_items = list(ref_medians.items()) + [("Your query", user_median_ms)]
    all_items.sort(key=lambda x: x[1])

    for label, ms in all_items:
        is_user = label == "Your query"
        flag = "[bold yellow]★ YOU[/]" if is_user else ""
        style = "bold yellow" if is_user else ""
        table.add_row(label, f"{ms:.2f}", flag, style=style)

    console.print(table)
    console.print(f"  Rank: [bold]{rank}[/] of {total} solutions\n")


def print_plan_summary(features: PlanFeatures) -> None:
    console.print(Rule("[bold]Query Plan Analysis[/]"))
    for line in features.summary_lines():
        console.print(f"  {line}")
    console.print()


def print_lint_warnings(warnings: list[LintWarning]) -> None:
    console.print(Rule("[bold]SQL Lint[/]"))
    if not warnings:
        console.print("  [green]No issues found.[/]\n")
        return
    for w in warnings:
        icon = "⚠" if w.severity == Severity.WARNING else "ℹ"
        color = "yellow" if w.severity == Severity.WARNING else "dim"
        console.print(f"  [{color}]{icon} [{w.code}][/] {w.message}")
    console.print()


def print_score_card(score: QueryScore) -> None:
    console.print(Rule("[bold]Score Card[/]"))
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Category", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Max", justify="right", style="dim")

    table.add_row("Correctness", f"{score.correctness_score:.0f}", "50")
    table.add_row("Runtime",     f"{score.runtime_score_val:.1f}", "25")
    table.add_row("Query Plan",  f"{score.plan_score:.1f}",        "15")
    table.add_row("SQL Style",   f"{score.lint_score_val:.0f}",    "10")
    table.add_row(
        "[bold]TOTAL[/]",
        f"[bold]{score.total:.1f}[/]",
        "[bold]100[/]",
    )

    console.print(table)
    console.print(
        f"\n  Grade: [{score.grade_color}][bold]{score.grade}[/][/]  "
        f"({score.total:.1f} / 100)\n"
    )


def print_explain_json(features: PlanFeatures) -> None:
    """Pretty-print the raw EXPLAIN JSON."""
    import json
    console.print_json(json.dumps(features.raw_plan, indent=2))
