"""QueryRank - PostgreSQL SQL practice and query evaluation CLI."""

import typer
from rich.console import Console

from queryrank.commands import (
    auth,
    challenge,
    evaluate,
)

app = typer.Typer(
    name="queryrank",
    help="[bold cyan]QueryRank[/] — Practice SQL. Measure efficiency. Rank your queries.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

# Register command groups
app.add_typer(auth.app, name=None)          # login, profile
app.add_typer(challenge.app, name=None)     # generate, list, start
app.add_typer(evaluate.app, name=None)      # submit, explain, benchmark


def main() -> None:
    app()


if __name__ == "__main__":
    main()
