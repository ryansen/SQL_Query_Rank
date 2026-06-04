"""PostgreSQL connection management for QueryRank."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


def get_dsn() -> str:
    """Build the PostgreSQL DSN from environment variables."""
    if dsn := os.getenv("DATABASE_URL"):
        return dsn

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "queryrank")
    user = os.getenv("POSTGRES_USER", "queryrank")
    password = os.getenv("POSTGRES_PASSWORD", "queryrank")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@contextmanager
def get_connection(
    autocommit: bool = False,
) -> Generator[psycopg.Connection, None, None]:
    """Yield an open psycopg connection, closing it on exit."""
    dsn = get_dsn()
    try:
        with psycopg.connect(dsn, autocommit=autocommit) as conn:
            yield conn
    except psycopg.OperationalError as exc:
        console.print(
            f"[bold red]✗[/] Cannot connect to PostgreSQL: {exc}\n"
            "[dim]Is Docker running?  Try: docker compose up -d[/]"
        )
        raise SystemExit(1)


def test_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except SystemExit:
        return False


def drop_schema(conn: psycopg.Connection, schema: str = "public") -> None:
    """Drop and recreate a schema (clean slate for each run)."""
    conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    conn.execute(f"CREATE SCHEMA {schema}")


def run_sql_file(conn: psycopg.Connection, path: str) -> None:
    """Execute every statement in a .sql file."""
    with open(path) as fh:
        sql = fh.read()
    conn.execute(sql)
