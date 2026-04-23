# ADU Agent Arena

Benchmarking coding agents on data-led research tasks drawn from real Autonomy Data Unit work.

## Architecture

Built on [Inspect AI](https://inspect.aisi.org.uk/). Agents are invoked via [pi-coding-agent](https://github.com/badlogic/pi-mono) inside Docker containers (`--mode json`). Each model/provider combination is a separate leaderboard entrant.

## Project layout

```
src/adu_arena/
  agents/pi_agent.py        # Inspect solver — execs pi inside Docker sandbox
  scorers/deterministic.py   # File, schema, row count, numeric, content checks
  scorers/judge.py           # Multi-judge scorer (multiple models × N runs)
  tasks/_common.py           # Shared dataset loader (maps workspace files via Sample.files)
  tasks/*.py                 # One @task per test

tests/<test-name>/
  DESCRIPTION.md             # Shown in leaderboard UI (links to code files)
  prompt.md                  # What the agent sees
  dataset.json               # Scoring configuration
  compose.yaml               # Docker sandbox (no bind mounts)
  workspace/                 # Input files only — copied into container per run

models.json                  # Configured models + judge config
scripts/
  run_all.py                 # Run tests with parallelism and auto-retry
  export_leaderboard.py      # logs/ + sessions/ + summaries/ → leaderboard.json
  generate_summaries.py      # Generate per-run narrative assessments
  publish.sh                 # Export → summaries → build → deploy
  results.py                 # CLI for viewing/managing results

web/                         # SvelteKit static leaderboard app
docker/Dockerfile            # Base image: Python + data-science libs + pi + Node
```

## Key design decisions

- **Isolated workspaces**: each run gets its own copy of workspace files via `Sample.files` (no bind mounts). Input files cannot be corrupted by agents.
- **Preserved workspaces**: after each run, the container's `/workspace` is archived to `workspaces/<timestamp>.tar.gz`.
- **Multi-judge scoring**: configured in `models.json` under `judges`. Multiple judge models each run N times; scores are averaged across all evaluations.
- **Flat logs**: all `.eval` files live in `logs/` (no subdirectories).
- **Generated data not committed**: `leaderboard.json`, `summaries/` are gitignored. Regenerate with `publish.sh` or the individual scripts.

## Running tests

```bash
# Run missing model+test combinations (reads models.json)
uv run python scripts/run_all.py

# Run all tests again (accumulates results for averaging)
uv run python scripts/run_all.py --rerun

# Run specific model or test
uv run python scripts/run_all.py --model anthropic/claude-sonnet-4-20250514
uv run python scripts/run_all.py --test csv_deduplicator

# Delete all results and start fresh
uv run python scripts/run_all.py --clear

# View results in terminal
uv run python scripts/results.py stats
uv run python scripts/results.py show --model qwen

# Delete specific results
uv run python scripts/results.py delete --model foo --yes
uv run python scripts/results.py delete --invalid --yes
```

## Publishing

```bash
bash scripts/publish.sh
```

This runs: export leaderboard → generate summaries → re-export with summaries → build SvelteKit app → deploy to AppGarden.

`leaderboard.json` must exist before `npm run build` (the prerenderer needs it).

## Adding a model

Add to `models.json`, then run `uv run python scripts/run_all.py` — it will only run the new model.

## Adding a test

1. Create `tests/<test-name>/` with `DESCRIPTION.md`, `prompt.md`, `dataset.json`, `compose.yaml`, `workspace/`
2. Create `src/adu_arena/tasks/<test_name>.py` with a `@task` function using `load_task_dataset()`
3. Add to `ALL_TASKS` in `scripts/run_all.py`

## Scoring

**Deterministic**: file existence, CSV schema, row counts, numeric aggregations, content checks. Configured in `dataset.json`.

**Judge**: multiple models × N runs (configured in `models.json`). Scores each dimension 1-10. Dimensions vary by archetype:
- `pipeline-stage`: correctness, methodology, completeness, code_quality
- `notebook-analysis`: correctness, methodology, completeness, code_quality
- `scrape-and-structure`: correctness, robustness, structure, code_quality
- `full-project-reproduction`: correctness, architecture, edge_cases, code_quality

**Auto-retry**: runs where the agent produced no files AND finished quickly AND the session contains provider errors are automatically retried (up to 3 attempts).

## Dependencies

- Python: `uv sync`
- Web: `cd web && npm install`
- Runtime: Docker must be running
- API keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` as needed
