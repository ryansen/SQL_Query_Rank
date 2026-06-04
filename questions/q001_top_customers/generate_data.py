"""Synthetic data generator for q001_top_customers."""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

fake = Faker()

SIZES = {
    "small":  {"customers": 50,    "orders": 200},
    "medium": {"customers": 500,   "orders": 5_000},
    "large":  {"customers": 5_000, "orders": 100_000},
}

REGIONS = ["North", "South", "East", "West", "Central"]
STATUSES = ["completed", "pending", "cancelled"]
STATUS_WEIGHTS = [0.60, 0.25, 0.15]     # 60% completed


def generate(conn, size: str = "medium") -> None:
    cfg = SIZES.get(size, SIZES["medium"])
    n_customers = cfg["customers"]
    n_orders = cfg["orders"]

    random.seed(42)
    Faker.seed(42)

    # --- Customers ---
    customers = []
    seen_emails: set[str] = set()
    for i in range(1, n_customers + 1):
        email = fake.unique.email()
        seen_emails.add(email)
        customers.append((i, fake.name(), email, random.choice(REGIONS)))

    conn.executemany(
        "INSERT INTO customers (id, name, email, region) VALUES (%s, %s, %s, %s)",
        customers,
    )

    # --- Orders ---
    # Introduce skew: top 10 customers get proportionally more orders
    top_customers = [c[0] for c in customers[:10]]
    start_date = date(2022, 1, 1)
    end_date   = date(2024, 12, 31)
    delta_days = (end_date - start_date).days

    orders = []
    for i in range(1, n_orders + 1):
        # 40% of orders go to the top 10 customers
        if random.random() < 0.40:
            cid = random.choice(top_customers)
        else:
            cid = random.randint(1, n_customers)

        order_date = start_date + timedelta(days=random.randint(0, delta_days))
        amount = round(random.uniform(10.0, 5_000.0), 2)
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        orders.append((i, cid, order_date, amount, status))

    conn.executemany(
        "INSERT INTO orders (id, customer_id, order_date, amount, status) "
        "VALUES (%s, %s, %s, %s, %s)",
        orders,
    )

    # Edge cases: a few customers with ONLY cancelled/pending orders
    edge_customer_id = n_customers + 1
    edge_email = "edge_no_completed@example.com"
    conn.execute(
        "INSERT INTO customers (id, name, email, region) VALUES (%s, %s, %s, %s)",
        (edge_customer_id, "Edge No-Sales", edge_email, "West"),
    )
    conn.execute(
        "INSERT INTO orders (id, customer_id, order_date, amount, status) "
        "VALUES (%s, %s, %s, %s, %s)",
        (n_orders + 1, edge_customer_id, date(2023, 6, 15), 999.99, "cancelled"),
    )

    # Reset sequences
    conn.execute(f"SELECT setval('customers_id_seq', {n_customers + 1})")
    conn.execute(f"SELECT setval('orders_id_seq', {n_orders + 1})")
