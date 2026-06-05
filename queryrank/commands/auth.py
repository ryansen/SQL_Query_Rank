"""Auth commands: login, profile."""

from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from queryrank.core import reporter
from queryrank.core.profile import UserProfile

app = typer.Typer(help="User profile management.")
console = Console()


@app.command()
def login(
    username: str = typer.Option(None, "--username", "-u", help="Your username"),
) -> None:
    """Log in or create a local QueryRank profile."""
    existing = UserProfile.load()

    if existing:
        console.print(
            f"[bold green]✓[/] Already logged in as [bold]{existing.username}[/].\n"
            "  Run [cyan]queryrank profile[/] to view stats, or "
            "[cyan]queryrank login --username new_name[/] to switch."
        )
        reporter.print_suggestions("queryrank list", "queryrank start q001_top_customers")
        return

    if not username:
        username = typer.prompt("Choose a username")

    username = username.strip()
    if not username:
        console.print("[red]Username cannot be empty.[/]")
        raise typer.Exit(1)

    profile = UserProfile(username=username)
    profile.save()
    console.print(f"[bold green]✓[/] Profile created for [bold]{username}[/]. Welcome to QueryRank!")
    reporter.print_suggestions("queryrank list", "queryrank start q001_top_customers")


@app.command()
def profile() -> None:
    """Display your QueryRank profile and stats."""
    p = UserProfile.load()
    if not p:
        console.print("[yellow]No profile found.[/] Run [cyan]queryrank login[/] first.")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]QueryRank Profile[/] - [bold]{p.username}[/]")
    console.print(f"  Member since: [dim]{p.created_at[:10]}[/]\n")

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Stat", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Questions attempted", str(len(p.questions_attempted)))
    table.add_row("Questions passed", str(len(p.questions_passed)))
    table.add_row("Pass rate", f"{p.pass_rate:.0f}%")
    table.add_row("Total score (sum of bests)", f"{p.total_score:.1f}")

    console.print(table)

    if p.best_scores:
        console.print("\n[dim]Best scores by question:[/]")
        for qid, sc in sorted(p.best_scores.items()):
            console.print(f"  {qid}: [bold]{sc:.1f}[/] / 100")
    console.print()
    reporter.print_suggestions("queryrank list", "queryrank start q001_top_customers")
