"""Synthetic data generator for this question."""

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
