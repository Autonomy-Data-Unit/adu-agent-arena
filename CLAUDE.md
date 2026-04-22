# ADU Agent Arena

Benchmarking coding agents on data-led research tasks drawn from real Autonomy Data Unit work.

## Architecture

Built on [Inspect AI](https://inspect.aisi.org.uk/) (UK AISI's evaluation framework). We write custom tasks, scorers, and a leaderboard on top.

- **Agent under test**: [pi-coding-agent](https://github.com/badlogic/pi-mono) — invoked inside Docker containers via `pi -p` (print mode)
- **Each model/provider combination** (e.g. `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o`) is a separate leaderboard entrant
- The `--model` flag passed to `inspect eval` determines which model pi-coding-agent uses

## Project layout

```
src/adu_arena/
  agents/pi_agent.py       # Inspect solver — execs pi inside Docker sandbox
  scorers/deterministic.py  # CSV checks: schema, row count, numeric, content
  scorers/excel.py          # Excel checks: sheet structure, numeric aggregation
  scorers/judge.py          # LLM-judge rubric templates per archetype
  tasks/*.py                # One @task function per test

tests/<test-name>/
  prompt.md                 # What the agent sees
  dataset.json              # Inspect Sample metadata + scoring config
  compose.yaml              # Docker Compose for this test's sandbox
  workspace/                # Starting files — bind-mounted into container
  fixtures/                 # Reference outputs for scoring (never shown to agent)

scripts/
  run_all.py                # Run all tests, optionally across multiple models
  export_leaderboard.py     # Inspect logs → web/static/leaderboard.json

web/                        # SvelteKit static leaderboard app
docker/Dockerfile           # Base image: Python + data-science libs + pi + Node
```

## Running tests

```bash
# Single test, single model
uv run inspect eval src/adu_arena/tasks/medrxiv_scraper.py@medrxiv_scraper \
  --model anthropic/claude-sonnet-4-20250514 --log-dir logs

# All tests, single model
uv run python scripts/run_all.py --model anthropic/claude-sonnet-4-20250514

# All tests, multiple models
uv run python scripts/run_all.py \
  --model anthropic/claude-sonnet-4-20250514 openai/gpt-4o

# Re-export leaderboard after runs
uv run python scripts/export_leaderboard.py

# Preview leaderboard
cd web && npm run build && npm run preview
```

## Adding a new test

1. Create `tests/<test-name>/` with `prompt.md`, `dataset.json`, `compose.yaml`, `workspace/`, and optionally `fixtures/`
2. Create `src/adu_arena/tasks/<test_name>.py` with a `@task` function
3. Add the task to `ALL_TASKS` in `scripts/run_all.py`
4. The `compose.yaml` must include `command: tail -f /dev/null` to keep the container alive

## Test archetypes

- `scrape-and-structure` — parse HTML/API responses into structured data
- `pipeline-stage` — transform frozen intermediate data
- `notebook-analysis` — produce analysis from raw data files
- `full-project-reproduction` — build a module from a spec

## Scoring design

Prefer deterministic checks. Avoid brittle checks that depend on:
- Exact whitespace or string formatting from HTML parsing
- Exact row/column counts when the merge strategy has legitimate variation (use tolerances)
- Exact column ordering

Good deterministic checks: numeric aggregation sums, file existence, schema column names, row counts with tolerance, presence of key substrings (e.g. surnames not full names).

Use LLM-judge scoring only for qualitative aspects (code clarity, methodology soundness).

## Dependencies

- Python: `uv sync` (uses pyproject.toml)
- Web: `cd web && npm install`
- Runtime: Docker must be running for test execution
