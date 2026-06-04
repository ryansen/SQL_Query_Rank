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

### Start PostgreSQL

```bash
cp .env.example .env          # edit if needed
docker compose up -d
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
```

This command:
1. Drops and recreates the question's schema in PostgreSQL.
2. Generates synthetic data (edge cases included).
3. Prints the question prompt and schema.
4. Creates `answer_q001_top_customers.sql` in your working directory.
5. Opens it in your `$EDITOR` (or the editor you specify).

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
- Check for SQL style issues (SELECT *, missing joins, etc.).
- Print a scored report with:
  - ✓/✗ Correctness (50 pts)
  - Runtime ranking vs. reference solutions (25 pts)
  - Query plan quality (15 pts)
  - SQL lint score (10 pts)
  - Final grade (S / A / B / C / D / F)

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
