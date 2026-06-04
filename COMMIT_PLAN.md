# QueryRank — Suggested Commit Plan

Follow this plan to build an organic, realistic git commit history.
Each commit represents a logical unit of work; spread across multiple sessions if needed.

---

## Phase 1 — Bootstrap

**Commit 1:** `chore: init project with uv and pyproject.toml`
- `pyproject.toml`
- `.gitignore`
- `.env.example`
- Empty `queryrank/__init__.py`

**Commit 2:** `chore: add Docker Compose for local PostgreSQL`
- `docker-compose.yml`

**Commit 3:** `docs: add README with usage and command reference`
- `README.md`

---

## Phase 2 — Core Infrastructure

**Commit 4:** `feat: add PostgreSQL connection module (core/db.py)`
- `queryrank/core/db.py`

**Commit 5:** `feat: add local user profile system (core/profile.py)`
- `queryrank/core/profile.py`

**Commit 6:** `feat: add question loader and discovery (core/questions.py)`
- `queryrank/core/questions.py`

---

## Phase 3 — Evaluation Engine

**Commit 7:** `feat: add query executor and correctness comparison`
- `queryrank/core/executor.py`

**Commit 8:** `feat: add EXPLAIN ANALYZE JSON parser`
- `queryrank/core/explain.py`

**Commit 9:** `feat: add benchmarking module with runtime scoring`
- `queryrank/core/benchmark.py`

**Commit 10:** `feat: add SQL linting checks`
- `queryrank/core/linter.py`

**Commit 11:** `feat: add scoring, ranking, and grade system`
- `queryrank/core/scoring.py`

**Commit 12:** `feat: add Rich terminal reporter`
- `queryrank/core/reporter.py`

---

## Phase 4 — CLI Commands

**Commit 13:** `feat: add CLI entry point with Typer`
- `queryrank/main.py`
- `queryrank/commands/__init__.py`

**Commit 14:** `feat: add login and profile commands`
- `queryrank/commands/auth.py`

**Commit 15:** `feat: add list and start challenge commands`
- `queryrank/commands/challenge.py`

**Commit 16:** `feat: add submit, explain, and benchmark commands`
- `queryrank/commands/evaluate.py`

---

## Phase 5 — Sample Questions

**Commit 17:** `feat: add q001 Top Customers question (schema + data + references)`
- `questions/q001_top_customers/config.json`
- `questions/q001_top_customers/prompt.md`
- `questions/q001_top_customers/schema.py`
- `questions/q001_top_customers/generate_data.py`
- `questions/q001_top_customers/references/solution_join.sql`
- `questions/q001_top_customers/references/solution_cte.sql`
- `questions/q001_top_customers/references/solution_window.sql`

**Commit 18:** `feat: add q002 Monthly Revenue question`
- `questions/q002_monthly_revenue/` (all files)

---

## Phase 6 — Polish

**Commit 19:** `fix: handle edge cases in correctness comparison (NULLs, Decimal)`
- Tweaks to `executor.py` as discovered during testing

**Commit 20:** `refactor: improve Rich report layout and color scheme`
- Tweaks to `reporter.py`

**Commit 21:** `chore: add dev dependencies and ruff config to pyproject.toml`
- `pyproject.toml` updates

**Commit 22:** `docs: update README with full scoring table and question format`
- `README.md` final pass

---

## Tips for Organic History

- Commit as you go, not all at once.
- Use past-tense verbs: "add", "fix", "refactor", "docs", "chore".
- Keep commits small and focused.
- Write the commit message before writing the code — it keeps you on track.
- `git commit --date="2024-XX-XX"` lets you backdate commits if recreating history.
