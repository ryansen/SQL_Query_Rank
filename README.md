# QueryRank

## Usage

QueryRank is a PostgreSQL-based SQL practice and query evaluation CLI. It helps you practice SQL interview questions by checking whether your query is correct and ranking how efficient it is compared to multiple reference solutions.

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Docker](https://www.docker.com/) (for the local PostgreSQL instance)

### Installation

```bash
uv add "git+https://github.com/<your-username>/queryrank.git"
```

Or clone and install locally:

```bash
git clone https://github.com/<your-username>/queryrank.git
cd queryrank
uv sync
```

To run `queryrank` directly instead of `uv run queryrank`, activate the project
virtualenv in each new terminal:

```bash
source .venv/Scripts/activate   # Git Bash on Windows
queryrank login --username alice
```

If `queryrank.exe` points at an old Python install, rebuild the virtualenv first:

```bash
rm -rf .venv
uv sync
source .venv/Scripts/activate
```

### Start PostgreSQL

```bash
cp .env.example .env          # edit if needed
docker compose up -d
```

If the container is running but `queryrank` reports `password authentication
failed for user "queryrank"`, reset the password stored in the existing Docker
volume:

```bash
docker exec -u postgres queryrank_postgres psql -U queryrank -d queryrank -c "ALTER USER queryrank WITH PASSWORD 'queryrank';"
```

---

### Commands

#### `queryrank login`

Create or display your local profile.

```bash
queryrank login --username alice
```

On first run this creates a profile saved at `~/.queryrank/profile.json`.  
On subsequent runs it confirms your current session.

---

#### `queryrank profile`

View your stats: questions attempted, pass rate, best scores.

```bash
queryrank profile
```

---

#### `queryrank list`

Browse all available SQL challenges with difficulty, tags, and your pass status.

```bash
queryrank list
```

---

#### `queryrank start <question_id>`

Set up the database for a challenge and open an answer file.

```bash
queryrank start q001_top_customers
queryrank start q001_top_customers --size large    # small | medium | large
queryrank start q001_top_customers --editor code   # specify your editor
queryrank start q001_top_customers --no-context-window
```

This command:
1. Drops and recreates the question's schema in PostgreSQL.
2. Generates synthetic data (edge cases included).
3. Prints the question prompt.
4. Creates `answer_q001_top_customers.sql` with the prompt and schema as comments.
5. Creates `context_q001_top_customers.md` as a separate reference file.
6. Opens both files in your `$EDITOR` (or the editor you specify).

---

#### `queryrank submit <question_id> <answer.sql>`

Submit your answer for full evaluation.

```bash
queryrank submit q001_top_customers answer_q001_top_customers.sql
queryrank submit q001_top_customers answer_q001_top_customers.sql --size large --runs 10
```

QueryRank will:
- Provision a fresh database with synthetic data.
- Run your query and compare it against all reference solutions.
- Benchmark your query and references (`--runs` iterations each).
- Run `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on your query.
- Check for SQL style and performance issues (SELECT *, missing joins, non-sargable filters, costly sorts, etc.).
- Explain likely reasons the query may be slow based on the query plan.
- Print a scored report with:
  - ✓/✗ Correctness (50 pts)
  - Runtime ranking vs. reference solutions (25 pts)
  - Query plan quality (15 pts)
  - SQL lint score (10 pts)
  - Final grade (S / A / B / C / D / F)
- Suggest the next useful command to run.

For a more stable final test, use a larger dataset and more benchmark runs:

```bash
queryrank submit q001_top_customers answer_q001_top_customers.sql --size large --runs 10
```

---

#### `queryrank explain <question_id> <answer.sql>`

Run `EXPLAIN ANALYZE` on your query and view the parsed plan summary.

```bash
queryrank explain q001_top_customers answer_q001_top_customers.sql
queryrank explain q001_top_customers answer_q001_top_customers.sql --raw   # full JSON
```

---

#### `queryrank benchmark <question_id> <answer.sql>`

Benchmark your query against reference solutions without full scoring.

```bash
queryrank benchmark q001_top_customers answer_q001_top_customers.sql --runs 20
```

---

### Scoring

| Category | Points |
|----------|--------|
| Correctness | 50 |
| Runtime vs. best reference | 25 |
| Query plan quality | 15 |
| SQL linting / style | 10 |
| **Total** | **100** |

Grades: **S** (≥90) · **A** (≥75) · **B** (≥60) · **C** (≥45) · **D** (≥30) · **F** (<30)

---

### Adding Questions

Each SQL challenge is a folder under `questions/`. The folder contains the
question text, the Python code that creates the database schema, the Python code
that generates synthetic data, and multiple reference SQL answers.

You can scaffold the folder first:

```bash
queryrank generate q003_late_shipments --title "Late Shipments" --difficulty medium --tags joins,dates,aggregation
```

Or use an OpenAI model to generate the whole challenge bundle:

```bash
export OPENAI_API_KEY=...
queryrank generate-ai q003_late_shipments --topic "ecommerce late shipments" --difficulty medium --tags joins,dates,aggregation
```

`generate-ai` reads `OPENAI_API_KEY` from your local environment and does not
write it to generated question files. Do not commit real keys; keep them in your
shell profile or local `.env`.

Place a folder in `questions/` with this structure:

```
questions/
  q003_your_question/
    config.json          # id, title, difficulty, tags
    prompt.md            # question description shown to the user
    schema.py            # create_schema(conn) function
    generate_data.py     # generate(conn, size) function
    references/
      solution_one.sql
      solution_two.sql
```

#### File responsibilities

- `config.json` tells QueryRank the question ID, title, difficulty, tags, and description.
- `prompt.md` is the user-facing question. It should state the schema, task, required output columns, ordering, and edge cases.
- `schema.py` defines `create_schema(conn)`. It should create tables, constraints, and indexes.
- `generate_data.py` defines `generate(conn, size="medium")`. It should insert deterministic synthetic data.
- `references/*.sql` are correct answers. QueryRank accepts a user answer if it matches any reference result.

#### Step 1: Write `config.json`

```json
{
  "id": "q003_late_shipments",
  "title": "Late Shipments",
  "difficulty": "medium",
  "tags": ["joins", "dates", "aggregation"],
  "default_dataset_size": "medium",
  "description": "Find carriers with the most late delivered shipments."
}
```

The `id` must match the folder name exactly.

#### Step 2: Write `prompt.md`

Be precise. The prompt is the contract that both user answers and reference
answers must satisfy.

```md
# Late Shipments

You have two tables: `orders` and `shipments`.

**orders**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | primary key |
| customer_region | TEXT | customer region |
| order_date | DATE | date the order was placed |

**shipments**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | primary key |
| order_id | INTEGER | FK to orders.id |
| carrier | TEXT | shipping carrier |
| shipped_date | DATE | date shipped |
| delivered_date | DATE | date delivered |
| promised_date | DATE | delivery deadline |
| status | TEXT | 'delivered', 'in_transit', 'cancelled' |

## Task

Return the top 5 carriers by number of late delivered shipments.

A shipment is late when:
- `status = 'delivered'`
- `delivered_date > promised_date`

Your result must include:
- `carrier`
- `late_shipments`
- `avg_days_late`

Order by `late_shipments` descending, then `carrier` ascending.
```

#### Step 3: Write `schema.py`

`schema.py` must expose `create_schema(conn)`. Use normal PostgreSQL DDL.

```python
"""Schema definition for q003_late_shipments."""


def create_schema(conn) -> None:
    conn.execute("""
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            customer_region TEXT NOT NULL,
            order_date DATE NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE shipments (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            carrier TEXT NOT NULL,
            shipped_date DATE NOT NULL,
            delivered_date DATE,
            promised_date DATE NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('delivered', 'in_transit', 'cancelled'))
        )
    """)

    conn.execute("CREATE INDEX idx_shipments_status_promised ON shipments(status, promised_date)")
    conn.execute("CREATE INDEX idx_shipments_order_id ON shipments(order_id)")
    conn.execute("CREATE INDEX idx_shipments_carrier ON shipments(carrier)")
```

Add indexes that match likely filters, joins, grouping, or ordering. This makes
benchmarks more interesting because good and bad queries can produce different
plans.

#### Step 4: Write `generate_data.py`

`generate_data.py` must expose `generate(conn, size="medium")`. It should be
deterministic, support `small`, `medium`, and `large`, and include edge cases.

```python
"""Synthetic data generator for q003_late_shipments."""

from __future__ import annotations

import random
from datetime import date, timedelta

SIZES = {
    "small": {"orders": 500},
    "medium": {"orders": 8_000},
    "large": {"orders": 200_000},
}

REGIONS = ["North", "South", "East", "West", "Central"]
CARRIERS = ["FastShip", "BoxRocket", "PostalPro", "SameDayNow"]
STATUSES = ["delivered", "in_transit", "cancelled"]
STATUS_WEIGHTS = [0.82, 0.12, 0.06]


def generate(conn, size: str = "medium") -> None:
    cfg = SIZES.get(size, SIZES["medium"])
    n_orders = cfg["orders"]

    random.seed(123)
    start = date(2023, 1, 1)
    delta_days = 365

    orders = []
    shipments = []

    for i in range(1, n_orders + 1):
        order_date = start + timedelta(days=random.randint(0, delta_days))
        region = random.choice(REGIONS)
        orders.append((i, region, order_date))

        carrier = random.choice(CARRIERS)
        shipped_date = order_date + timedelta(days=random.randint(0, 3))
        promised_date = shipped_date + timedelta(days=random.randint(2, 7))
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]

        if status == "delivered":
            # Roughly 25% of delivered shipments are late.
            extra_days = random.choice([0, 0, 0, 1, 2, 3, 5])
            delivered_date = promised_date + timedelta(days=extra_days)
        else:
            delivered_date = None

        shipments.append((
            i,
            i,
            carrier,
            shipped_date,
            delivered_date,
            promised_date,
            status,
        ))

    # Edge case: delivered exactly on promised_date, not late.
    edge_id = n_orders + 1
    orders.append((edge_id, "North", date(2023, 6, 1)))
    shipments.append((
        edge_id,
        edge_id,
        "FastShip",
        date(2023, 6, 2),
        date(2023, 6, 5),
        date(2023, 6, 5),
        "delivered",
    ))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO orders (id, customer_region, order_date) VALUES (%s, %s, %s)",
            orders,
        )
        cur.executemany(
            """
            INSERT INTO shipments (
                id, order_id, carrier, shipped_date, delivered_date, promised_date, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            shipments,
        )

    conn.execute(f"SELECT setval('orders_id_seq', {edge_id})")
    conn.execute(f"SELECT setval('shipments_id_seq', {edge_id})")
```

Useful data-generation rules:

- Always call `random.seed(...)` so results are reproducible.
- Make `large` big enough for benchmark differences to show.
- Add edge cases: ties, zero-match rows, exact boundary dates, cancelled rows, NULLs when relevant, duplicate-looking rows, and rows that should be excluded.
- Use `cursor.executemany(...)` for bulk inserts.
- Keep generated data realistic enough that query plans resemble real work.

#### Step 5: Write three reference answers

Reference files live in `references/`. They should all return the same columns,
same values, and required ordering.

`references/solution_join.sql`

```sql
SELECT
    s.carrier,
    COUNT(*) AS late_shipments,
    AVG(s.delivered_date - s.promised_date) AS avg_days_late
FROM shipments AS s
JOIN orders AS o
    ON o.id = s.order_id
WHERE s.status = 'delivered'
  AND s.delivered_date > s.promised_date
GROUP BY s.carrier
ORDER BY late_shipments DESC, s.carrier ASC
LIMIT 5;
```

`references/solution_cte.sql`

```sql
WITH late AS (
    SELECT
        carrier,
        delivered_date - promised_date AS days_late
    FROM shipments
    WHERE status = 'delivered'
      AND delivered_date > promised_date
)
SELECT
    carrier,
    COUNT(*) AS late_shipments,
    AVG(days_late) AS avg_days_late
FROM late
GROUP BY carrier
ORDER BY late_shipments DESC, carrier ASC
LIMIT 5;
```

`references/solution_alt.sql`

```sql
SELECT
    carrier,
    late_shipments,
    avg_days_late
FROM (
    SELECT
        s.carrier,
        COUNT(*) AS late_shipments,
        AVG(s.delivered_date - s.promised_date) AS avg_days_late
    FROM shipments AS s
    WHERE s.status = 'delivered'
      AND s.delivered_date > s.promised_date
    GROUP BY s.carrier
) AS ranked
ORDER BY late_shipments DESC, carrier ASC
LIMIT 5;
```

Each question should include three correct reference SQL files. Aim for:

- a straightforward readable solution
- a CTE or pre-aggregation solution
- an alternative approach, such as a window-function version or a differently ordered join

Good generated questions should have deterministic data (`random.seed(...)`),
small/medium/large sizes, and edge cases that catch common wrong answers, such as
ties, zero-match rows, duplicate values, NULLs if relevant, cancelled/pending
records, or date-boundary rows.

#### Step 6: Test the question

Start the challenge and inspect the generated answer/context files:

```bash
queryrank start q003_late_shipments --size small --editor "code -n"
```

Submit one of your reference answers as a sanity check:

```bash
queryrank submit q003_late_shipments questions/q003_late_shipments/references/solution_join.sql --size small --runs 3
```

Then test a larger benchmark:

```bash
queryrank submit q003_late_shipments questions/q003_late_shipments/references/solution_join.sql --size large --runs 10
```

If a reference solution fails correctness, the prompt, data generator, or one of
the references is inconsistent. Fix that before asking users to solve the
question.

### Configuration

All PostgreSQL settings are read from environment variables (or a `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | DB host |
| `POSTGRES_PORT` | `5432` | DB port |
| `POSTGRES_DB` | `queryrank` | Database name |
| `POSTGRES_USER` | `queryrank` | DB user |
| `POSTGRES_PASSWORD` | `queryrank` | DB password |
| `DATABASE_URL` | — | Full DSN (overrides above) |
