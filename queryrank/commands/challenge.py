"""Challenge commands: generate, list, start."""

from __future__ import annotations

import json
import os
import re
import subprocess
import shlex
import urllib.error
import urllib.request
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from queryrank.core import reporter
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
    context_window: bool = typer.Option(
        True,
        "--context-window/--no-context-window",
        help="Open a separate question/schema reference file next to your answer.",
    ),
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
        schema_summary = _describe_schema(conn)
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
            _answer_template(q, question_id, size, schema_summary),
            encoding="utf-8",
        )
        console.print(f"[green]✓[/] Created [bold]{answer_path.name}[/]")
    else:
        _ensure_answer_context(answer_path, q, question_id, size, schema_summary)
        console.print(f"[dim]Using existing[/] {answer_path.name}")

    context_path = Path.cwd() / f"context_{question_id}.md"
    if context_window:
        context_path.write_text(
            _context_markdown(q, question_id, size, schema_summary),
            encoding="utf-8",
        )
        console.print(f"[green]✓[/] Reference saved to [bold]{context_path.name}[/]")

    # Open editor
    _open_editor(answer_path, editor, extra_paths=[context_path] if context_window else [])
    console.print(
        f"\nWhen done, run:\n"
        f"  [cyan]queryrank submit {question_id} {answer_path.name}[/]\n"
    )
    reporter.print_suggestions(
        f"queryrank submit {question_id} {answer_path.name} --size large --runs 10",
        f"queryrank explain {question_id} {answer_path.name} --size large",
    )


@app.command()
def generate(
    question_id: str = typer.Argument(..., help="Question ID, e.g. q003_late_shipments"),
    title: str = typer.Option("", "--title", "-t", help="Human-readable title"),
    difficulty: str = typer.Option("medium", "--difficulty", "-d", help="easy | medium | hard"),
    tags: str = typer.Option("aggregation", "--tags", help="Comma-separated tags"),
) -> None:
    """Scaffold a new question folder with prompt, schema, data, and references."""
    question_id = _normalise_question_id(question_id)
    if difficulty not in {"easy", "medium", "hard"}:
        console.print("[red]Difficulty must be one of: easy, medium, hard[/]")
        raise typer.Exit(1)

    root = Path(__file__).parent.parent.parent / "questions" / question_id
    if root.exists():
        console.print(f"[red]Question already exists:[/] {root}")
        raise typer.Exit(1)

    title = title.strip() or _title_from_question_id(question_id)
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    (root / "references").mkdir(parents=True)
    (root / "config.json").write_text(
        json.dumps(
            {
                "id": question_id,
                "title": title,
                "difficulty": difficulty,
                "tags": tag_list,
                "default_dataset_size": "medium",
                "description": "TODO: one-sentence description of the task.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "prompt.md").write_text(_prompt_template(title), encoding="utf-8")
    (root / "schema.py").write_text(_schema_template(), encoding="utf-8")
    (root / "generate_data.py").write_text(_data_template(), encoding="utf-8")

    refs = {
        "solution_join.sql": _reference_template("Straightforward join/group-by solution"),
        "solution_cte.sql": _reference_template("CTE or pre-aggregation solution"),
        "solution_alt.sql": _reference_template("Alternative valid approach"),
    }
    for name, text in refs.items():
        (root / "references" / name).write_text(text, encoding="utf-8")

    console.print(f"[green]✓[/] Created [bold]{question_id}[/] at {root}")
    reporter.print_suggestions(
        f"queryrank start {question_id}",
        f"queryrank submit {question_id} answer_{question_id}.sql --size large --runs 10",
    )


@app.command("generate-ai")
def generate_ai(
    question_id: str = typer.Argument(..., help="Question ID, e.g. q003_late_shipments"),
    topic: str = typer.Option(..., "--topic", "-t", help="Business/data topic for the challenge"),
    difficulty: str = typer.Option("medium", "--difficulty", "-d", help="easy | medium | hard"),
    tags: str = typer.Option("aggregation,joins", "--tags", help="Comma-separated tags"),
    model: str = typer.Option("gpt-5.4-mini", "--model", help="OpenAI model to use"),
) -> None:
    """Use OpenAI to generate a complete question bundle."""
    question_id = _normalise_question_id(question_id)
    if difficulty not in {"easy", "medium", "hard"}:
        console.print("[red]Difficulty must be one of: easy, medium, hard[/]")
        raise typer.Exit(1)

    root = Path(__file__).parent.parent.parent / "questions" / question_id
    if root.exists():
        console.print(f"[red]Question already exists:[/] {root}")
        raise typer.Exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]OPENAI_API_KEY is not set.[/]")
        console.print("[dim]Set it, then rerun this command. Example: export OPENAI_API_KEY=...[/]")
        raise typer.Exit(1)

    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    console.print(f"[cyan]Generating[/] {question_id} with {model}...")
    artifact = _call_openai_question_agent(
        api_key=api_key,
        model=model,
        question_id=question_id,
        topic=topic,
        difficulty=difficulty,
        tags=tag_list,
    )
    _write_ai_question(root, question_id, artifact)

    console.print(f"[green]✓[/] Generated [bold]{question_id}[/] at {root}")
    reporter.print_suggestions(
        f"queryrank start {question_id}",
        f"queryrank submit {question_id} answer_{question_id}.sql --size large --runs 10",
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


def _normalise_question_id(question_id: str) -> str:
    question_id = question_id.strip().lower().replace("-", "_")
    if not re.fullmatch(r"q\d{3}_[a-z0-9_]+", question_id):
        console.print("[red]Question ID must look like q003_late_shipments[/]")
        raise typer.Exit(1)
    return question_id


def _title_from_question_id(question_id: str) -> str:
    words = question_id.split("_")[1:]
    return " ".join(word.capitalize() for word in words)


def _prompt_template(title: str) -> str:
    return f"""# {title}

TODO: Describe the business scenario and the table(s) available.

## Schema

TODO: List each table and its columns.

## Task

Write a query that returns TODO.

Your result must include:
- `TODO_column`

Ordered by TODO.

## Hints

- TODO: include one useful hint.
"""


def _schema_template() -> str:
    return '''"""Schema definition for this question."""


def create_schema(conn) -> None:
    """Create the tables needed for this question."""
    conn.execute("""
        CREATE TABLE example_table (
            id SERIAL PRIMARY KEY,
            created_at DATE NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            status TEXT NOT NULL
        )
    """)

    conn.execute("CREATE INDEX idx_example_table_status ON example_table(status)")
'''


def _data_template() -> str:
    return '''"""Synthetic data generator for this question."""

from __future__ import annotations

import random
from datetime import date, timedelta

SIZES = {
    "small": 500,
    "medium": 8_000,
    "large": 200_000,
}

STATUSES = ["completed", "pending", "cancelled"]
WEIGHTS = [0.60, 0.25, 0.15]


def generate(conn, size: str = "medium") -> None:
    n = SIZES.get(size, SIZES["medium"])
    random.seed(42)

    start = date(2022, 1, 1)
    delta_days = (date(2024, 12, 31) - start).days

    rows = []
    for i in range(1, n + 1):
        rows.append((
            i,
            start + timedelta(days=random.randint(0, delta_days)),
            round(random.uniform(5.0, 10_000.0), 2),
            random.choices(STATUSES, weights=WEIGHTS, k=1)[0],
        ))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO example_table (id, created_at, amount, status) VALUES (%s, %s, %s, %s)",
            rows,
        )
'''


def _reference_template(label: str) -> str:
    return f"""-- {label}
-- TODO: replace this with a correct reference query.
-- All reference solutions should return the same columns, row values, and required ordering.

SELECT
    status AS todo_column
FROM example_table
ORDER BY status;
"""


def _call_openai_question_agent(
    *,
    api_key: str,
    model: str,
    question_id: str,
    topic: str,
    difficulty: str,
    tags: list[str],
) -> dict:
    prompt = _ai_generation_prompt(question_id, topic, difficulty, tags)
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You generate complete PostgreSQL SQL practice challenges. "
                    "Return only valid JSON, with no Markdown fences or commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": 12000,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        console.print(f"[red]OpenAI request failed:[/] {exc.code} {body}")
        raise typer.Exit(1) from exc
    except urllib.error.URLError as exc:
        console.print(f"[red]OpenAI request failed:[/] {exc.reason}")
        raise typer.Exit(1) from exc

    text = _response_text(raw)
    try:
        artifact = json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        console.print("[red]The model did not return valid JSON.[/]")
        console.print(text[:2000])
        raise typer.Exit(1) from exc

    _validate_ai_artifact(artifact)
    return artifact


def _ai_generation_prompt(question_id: str, topic: str, difficulty: str, tags: list[str]) -> str:
    return f"""
Create a complete QueryRank PostgreSQL challenge bundle.

Question ID: {question_id}
Topic: {topic}
Difficulty: {difficulty}
Tags: {", ".join(tags)}

Return exactly this JSON object:
{{
  "config": {{
    "id": "{question_id}",
    "title": "...",
    "difficulty": "{difficulty}",
    "tags": {json.dumps(tags)},
    "default_dataset_size": "medium",
    "description": "..."
  }},
  "prompt_md": "...",
  "schema_py": "...",
  "generate_data_py": "...",
  "references": {{
    "solution_join.sql": "...",
    "solution_cte.sql": "...",
    "solution_alt.sql": "..."
  }}
}}

Requirements:
- Use PostgreSQL syntax.
- schema_py must define create_schema(conn) and create useful indexes.
- generate_data_py must define generate(conn, size="medium").
- generate_data_py must be deterministic with random.seed(...).
- generate_data_py must support small, medium, and large sizes.
- generate_data_py must create edge cases that catch common wrong answers.
- Use cursor.executemany for bulk inserts.
- Each reference SQL file must be correct and return the exact same columns and ordering.
- The three reference SQL files should use meaningfully different approaches.
- Do not include destructive filesystem code, network calls, subprocess calls, or imports outside the standard library plus faker if useful.
""".strip()


def _response_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    chunks: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks)


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_ai_artifact(artifact: dict) -> None:
    required = {"config", "prompt_md", "schema_py", "generate_data_py", "references"}
    missing = sorted(required - set(artifact))
    if missing:
        console.print(f"[red]AI response missing keys:[/] {', '.join(missing)}")
        raise typer.Exit(1)
    if not isinstance(artifact["references"], dict) or len(artifact["references"]) < 3:
        console.print("[red]AI response must include at least three reference SQL files.[/]")
        raise typer.Exit(1)


def _write_ai_question(root: Path, question_id: str, artifact: dict) -> None:
    config = dict(artifact["config"])
    config["id"] = question_id

    (root / "references").mkdir(parents=True)
    (root / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (root / "prompt.md").write_text(str(artifact["prompt_md"]).strip() + "\n", encoding="utf-8")
    (root / "schema.py").write_text(str(artifact["schema_py"]).strip() + "\n", encoding="utf-8")
    (root / "generate_data.py").write_text(
        str(artifact["generate_data_py"]).strip() + "\n",
        encoding="utf-8",
    )

    for filename, sql in artifact["references"].items():
        safe_name = Path(filename).name
        if not safe_name.endswith(".sql"):
            safe_name += ".sql"
        (root / "references" / safe_name).write_text(str(sql).strip() + "\n", encoding="utf-8")


def _open_editor(path: Path, editor: str, extra_paths: list[Path] | None = None) -> None:
    import os
    import shutil

    cmd = editor or os.getenv("EDITOR") or os.getenv("VISUAL") or ""
    if not cmd:
        for fallback in ("nano", "vim", "vi", "notepad"):
            if shutil.which(fallback):
                cmd = fallback
                break

    cmd_parts = shlex.split(cmd) if cmd else []
    executable = cmd_parts[0] if cmd_parts else ""
    paths = [path, *(extra_paths or [])]

    if executable and shutil.which(executable):
        if _is_gui_editor(executable):
            for open_path in paths:
                subprocess.Popen([*cmd_parts, str(open_path)])  # noqa: S603
        else:
            subprocess.run([*cmd_parts, str(path)])
            for extra_path in extra_paths or []:
                console.print(f"[dim]Reference file: {extra_path}[/]")
    else:
        console.print(f"[dim]No editor found. Edit manually: {path}[/]")
        for extra_path in extra_paths or []:
            console.print(f"[dim]Reference file: {extra_path}[/]")


def _is_gui_editor(executable: str) -> bool:
    name = Path(executable).name.lower()
    return name in {
        "code",
        "code.exe",
        "notepad",
        "notepad.exe",
        "notepad++",
        "notepad++.exe",
        "subl",
        "subl.exe",
        "atom",
        "atom.exe",
    }


def _answer_template(q, question_id: str, size: str, schema_summary: str) -> str:  # type: ignore[no-untyped-def]
    return (
        _answer_context(q, question_id, size, schema_summary)
        + "\n"
        + "-- Write your SQL query below. Only executable SQL is evaluated.\n\n"
    )


def _answer_context(q, question_id: str, size: str, schema_summary: str) -> str:  # type: ignore[no-untyped-def]
    sections = [
        f"QueryRank: {q.config.title}",
        f"Question:  {question_id}",
        f"Dataset:   {size}",
        "",
        "Prompt",
        "------",
        q.prompt.strip(),
        "",
        "Database Schema",
        "---------------",
        schema_summary.strip(),
    ]
    return "-- QUERYRANK CONTEXT START\n" + _sql_comment("\n".join(sections)) + "\n-- QUERYRANK CONTEXT END\n"


def _context_markdown(q, question_id: str, size: str, schema_summary: str) -> str:  # type: ignore[no-untyped-def]
    return (
        f"# {q.config.title}\n\n"
        f"- Question: `{question_id}`\n"
        f"- Difficulty: `{q.config.difficulty}`\n"
        f"- Dataset: `{size}`\n"
        f"- Tags: {', '.join(f'`{tag}`' for tag in q.config.tags)}\n\n"
        "## Prompt\n\n"
        f"{q.prompt.strip()}\n\n"
        "## Database Schema\n\n"
        "```text\n"
        f"{schema_summary.strip()}\n"
        "```\n"
    )


def _sql_comment(text: str) -> str:
    return "\n".join("--" if not line else f"-- {line}" for line in text.splitlines())


def _ensure_answer_context(
    answer_path: Path,
    q,  # type: ignore[no-untyped-def]
    question_id: str,
    size: str,
    schema_summary: str,
) -> None:
    current = answer_path.read_text(encoding="utf-8")
    if "-- QUERYRANK CONTEXT START" in current:
        return
    answer_path.write_text(
        _answer_context(q, question_id, size, schema_summary)
        + "\n"
        + current,
        encoding="utf-8",
    )


def _describe_schema(conn) -> str:  # type: ignore[no-untyped-def]
    rows = conn.execute("""
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """).fetchall()

    if not rows:
        return "No public tables found."

    lines: list[str] = []
    current_table: str | None = None
    for table_name, column_name, data_type, is_nullable, column_default in rows:
        if table_name != current_table:
            if current_table is not None:
                lines.append("")
            lines.append(str(table_name))
            current_table = table_name

        nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
        default = f" DEFAULT {column_default}" if column_default else ""
        lines.append(f"  - {column_name}: {data_type} {nullable}{default}")

    return "\n".join(lines)
