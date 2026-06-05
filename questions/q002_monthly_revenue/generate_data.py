"""Data generator for q002_monthly_revenue."""

from __future__ import annotations

import random
from datetime import date, timedelta

SIZES = {
    "small":  500,
    "medium": 8_000,
    "large":  200_000,
}

STATUSES = ["completed", "pending", "cancelled"]
WEIGHTS  = [0.60, 0.25, 0.15]


def generate(conn, size: str = "medium") -> None:
    n = SIZES.get(size, SIZES["medium"])
    random.seed(7)

    start = date(2022, 1, 1)
    end   = date(2024, 12, 31)
    delta = (end - start).days

    rows = []
    for i in range(1, n + 1):
        d = start + timedelta(days=random.randint(0, delta))
        amount = round(random.uniform(5.0, 10_000.0), 2)
        status = random.choices(STATUSES, weights=WEIGHTS, k=1)[0]
        rows.append((i, d, amount, status))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO orders (id, order_date, amount, status) VALUES (%s, %s, %s, %s)",
            rows,
        )
