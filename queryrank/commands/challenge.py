"""Challenge commands: generate, list, start."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from queryrank.core.questions import list_questions, get_question
from queryrank.core.profile import UserProfile
from queryrank.core.db import get_connection

app = typer.Typer(help="Browse and start SQL challenges.")
console = Console()


@app.command("list")
def list_cmd() -> None:
    """List all available SQL challenges."""
    questions = list_questions()
    if not questions:
        console.print("[yellow]No questions found.[/] Add question folders to the questions/ directory.")
        return

    profile = UserProfile.load()
    passed = set(profile.questions_passed) if profile else set()

    table = Table(title="Available Challenges", box=box.ROUNDED, show_lines=True)
    table.add_column("ID",         style="cyan",   no_wrap=True)
    table.add_column("Title",      style="bold")
    table.add_column("Difficulty")
    table.add_column("Tags",       style="dim")
    table.add_column("Status",     justify="center")

    for q in questions:
        diff = q.config.difficulty
        color = {"easy": "green", "medium": "yellow", "hard": "red"}.get(diff, "white")
        status = "[green]✓ Passed[/]" if q.id in passed else "[dim]—[/]"
        table.add_row(
            q.id,
            q.config.title,
            f"[{color}]{diff}[/]",
            ", ".join(q.config.tags),
            status,
        )

    console.print(table)


@app.command()
def start(
    question_id: str = typer.Argument(..., help="Question ID (e.g. q001_top_customers)"),
    size: str = typer.Option("medium", "--size", "-s", help="Dataset size: small | medium | large"),
    editor: str = typer.Option("", "--editor", "-e", help="Editor to open (default: $EDITOR)"),
) -> None:
    """
    Set up a challenge and open an answer file for editing.

    Provisions the database, generates data, and opens answer.sql
    in your preferred editor.
    """
    _require_profile()
    q = _require_question(question_id)

    console.print(f"\n[bold cyan]Setting up[/] [bold]{q.config.title}[/] ({size} dataset)…")

    with get_connection(autocommit=True) as conn:
        from queryrank.core.db import drop_schema
        drop_schema(conn)
        q.setup_schema(conn)
        q.generate_data(conn, size=size)
        conn.execute("COMMIT") if not conn.autocommit else None  # type: ignore[attr-defined]

    console.print("[green]✓[/] Database ready.")

    # Display prompt
    from queryrank.core.reporter import print_question_header, print_prompt
    print_question_header(q.config.title, q.config.difficulty, q.config.tags)
    print_prompt(q.prompt)

    # Create answer file in cwd
    answer_path = Path.cwd() / f"answer_{question_id}.sql"
    if not answer_path.exists():
        answer_path.write_text(
            f"-- QueryRank: {q.config.title}\n"
            f"-- Question:  {question_id}\n\n"
            "-- Write your SQL query below:\n\n"
        )
        console.print(f"[green]✓[/] Created [bold]{answer_path.name}[/]")
    else:
        console.print(f"[dim]Using existing[/] {answer_path.name}")

    # Open editor
    _open_editor(answer_path, editor)
    console.print(
        f"\nWhen done, run:\n"
        f"  [cyan]queryrank submit {question_id} {answer_path.name}[/]\n"
    )


@app.command()
def generate() -> None:
    """(Placeholder) Generate a new question with AI assistance."""
    console.print(
        "[dim]The 'generate' command is reserved for AI-assisted question generation.[/]\n"
        "For the MVP, add question folders manually to the questions/ directory."
    )


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
        console.print(f"[red]Question '{question_id}' not found.[/] Run [cyan]queryrank list[/] to see available questions.")
        raise typer.Exit(1)
    return q


def _open_editor(path: Path, editor: str) -> None:
    import os
    import shutil

    cmd = editor or os.getenv("EDITOR") or os.getenv("VISUAL") or ""
    if not cmd:
        for fallback in ("nano", "vim", "vi", "notepad"):
            if shutil.which(fallback):
                cmd = fallback
                break

    if cmd and shutil.which(cmd):
        subprocess.run([cmd, str(path)])
    else:
        console.print(f"[dim]No editor found. Edit manually: {path}[/]")
