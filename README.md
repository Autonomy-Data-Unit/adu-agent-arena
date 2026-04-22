# ADU Agent Arena

Benchmarking coding agents on data-led research tasks drawn from real [Autonomy Data Unit](https://github.com/Autonomy-Data-Unit) work.

**Live leaderboard:** [adu-agent-arena.apps.autonomy.work](https://adu-agent-arena.apps.autonomy.work)

Built on [Inspect AI](https://inspect.aisi.org.uk/) with [pi-coding-agent](https://github.com/badlogic/pi-mono) as the agent runtime. Each model/provider combination is a separate leaderboard entrant, scored by both deterministic checks and an LLM judge (Claude Opus 4.7).

## Quick start

```bash
# Install dependencies
uv sync
cd web && npm install && cd ..

# Run all tests for all configured models (skips already-completed runs)
uv run python scripts/run_all.py

# Export results and publish leaderboard
bash scripts/publish.sh
```

## Running tests

### Run all models on all tests

```bash
uv run python scripts/run_all.py
```

This reads models from [`models.json`](models.json) and runs every model/test combination that hasn't already succeeded. Results are saved to `logs/`.

### Run specific models or tests

```bash
# One model, all tests
uv run python scripts/run_all.py --model anthropic/claude-sonnet-4-20250514

# One test, all models
uv run python scripts/run_all.py --test gov_contracts_scraper

# Specific combination
uv run python scripts/run_all.py --model openai/gpt-5.4 --test csv_deduplicator

# See what would run without running it
uv run python scripts/run_all.py --list

# Force re-run even if results exist
uv run python scripts/run_all.py --force
```

### Run directly with Inspect CLI

```bash
uv run inspect eval src/adu_arena/tasks/gov_contracts.py@gov_contracts_scraper \
  --model anthropic/claude-sonnet-4-20250514 --log-dir logs
```

## Adding a new model

Edit [`models.json`](models.json) and add an entry:

```json
{
  "id": "openrouter/deepseek/deepseek-v3.2",
  "label": "DeepSeek V3.2",
  "tier": "open-source"
}
```

Then run `uv run python scripts/run_all.py` — it will automatically run only the new model since existing results are skipped.

**Supported providers:** `anthropic`, `openai`, `openrouter`, `google`, `mistral`, `deepseek`, `groq`. Set the corresponding API key as an environment variable (e.g. `OPENROUTER_API_KEY`).

## Creating a new test

### 1. Create the test directory

```
tests/<test-name>/
├── DESCRIPTION.md      # Human-readable description (shown in leaderboard UI)
├── prompt.md           # The task given to the agent
├── dataset.json        # Scoring configuration (deterministic checks)
├── compose.yaml        # Docker sandbox config
└── workspace/          # Starting files (mounted into the container)
```

### 2. Write the prompt

`prompt.md` is what the agent sees. Be specific about:
- What input files are available and their format
- Exactly what output files to produce
- The expected output format (column names, JSON keys, etc.)

### 3. Define deterministic checks

`dataset.json` configures what the scorer checks automatically:

```json
[
  {
    "input": "file://prompt.md",
    "target": "Brief description of expected output",
    "metadata": {
      "archetype": "pipeline-stage",
      "checks": {
        "expected_files": ["/workspace/output.csv"],
        "csv_schema": {
          "file": "/workspace/output.csv",
          "columns": ["col1", "col2", "col3"]
        },
        "row_count": {
          "file": "/workspace/output.csv",
          "expected": 100
        },
        "content_present": {
          "file": "/workspace/output.csv",
          "strings": ["expected_value_1", "expected_value_2"]
        },
        "numeric_checks": [
          {"file": "/workspace/output.csv", "column": "col2", "aggregation": "sum", "expected": 12345.0, "tolerance": 1.0}
        ]
      }
    }
  }
]
```

Available check types: `expected_files`, `csv_schema`, `row_count`, `content_present`, `content_absent`, `numeric_checks`.

### 4. Create the Docker compose file

```yaml
services:
  default:
    build:
      context: ../../docker
      dockerfile: Dockerfile
    command: tail -f /dev/null
    working_dir: /workspace
    volumes:
      - ./workspace:/workspace
```

### 5. Create the task definition

Add `src/adu_arena/tasks/<test_name>.py`:

```python
import json
from pathlib import Path
from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from adu_arena.agents.pi_agent import pi_coding_agent
from adu_arena.scorers.deterministic import deterministic_scorer
from adu_arena.scorers.judge import judge_scorer

TEST_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "<test-name>"

def _load_dataset() -> MemoryDataset:
    prompt = (TEST_DIR / "prompt.md").read_text()
    raw = json.loads((TEST_DIR / "dataset.json").read_text())
    return MemoryDataset([
        Sample(input=prompt, target=e["target"], metadata=e["metadata"])
        for e in raw
    ])

@task
def my_test(timeout: int = 600) -> Task:
    return Task(
        dataset=_load_dataset(),
        solver=pi_coding_agent(timeout=timeout),
        scorer=[
            deterministic_scorer(),
            judge_scorer(archetype="pipeline-stage"),
        ],
        sandbox=("docker", str(TEST_DIR / "compose.yaml")),
        time_limit=timeout + 60,
        token_limit=300_000,
    )
```

### 6. Register the test

Add the import to [`scripts/run_all.py`](scripts/run_all.py) in the `ALL_TASKS` dict.

### 7. Verify

```bash
# Run the test with one model
uv run python scripts/run_all.py --model anthropic/claude-sonnet-4-20250514 --test my_test

# Check results
uv run inspect view --log-dir logs
```

## Scoring

Each test has two scorers:

**Deterministic scorer** — checks file existence, CSV schemas, row counts, numeric values, and string content. Pass/fail, no ambiguity.

**LLM judge** (Claude Opus 4.7) — reads the agent's code from the sandbox and scores on a 1-10 scale across dimensions that vary by test archetype:

| Archetype | Dimensions |
|---|---|
| `pipeline-stage` | correctness, methodology, completeness, code_quality |
| `notebook-analysis` | correctness, methodology, completeness, code_quality |
| `scrape-and-structure` | correctness, robustness, structure, code_quality |
| `full-project-reproduction` | correctness, architecture, edge_cases, code_quality |

## Current tests

| Test | Archetype | Description |
|---|---|---|
| [`staffing-analysis`](tests/staffing-analysis/) | pipeline-stage | Merge QPSES + NOMIS data, compute per-capita employment rates |
| [`culture-spending-analysis`](tests/culture-spending-analysis/) | notebook-analysis | Analyse 15 years of UK local authority culture spending |
| [`gov-contracts-scraper`](tests/gov-contracts-scraper/) | scrape-and-structure | Parse HTML of UK government contract awards |
| [`csv-deduplicator`](tests/csv-deduplicator/) | full-project-reproduction | Build a company record deduplication module |

## Project structure

```
src/adu_arena/
  agents/pi_agent.py        # Pi-coding-agent solver (execs pi inside Docker)
  scorers/deterministic.py   # File, schema, numeric, content checks
  scorers/judge.py           # Per-dimension LLM judge (1-10 scale)
  tasks/*.py                 # One @task per test

tests/<test-name>/
  DESCRIPTION.md             # Shown in leaderboard UI
  prompt.md                  # What the agent sees
  dataset.json               # Scoring config
  compose.yaml               # Docker sandbox
  workspace/                 # Input files

scripts/
  run_all.py                 # Run tests, skip completed combinations
  export_leaderboard.py      # Inspect logs -> leaderboard.json
  publish.sh                 # Build + deploy to AppGarden

models.json                  # Configured models to benchmark
web/                         # SvelteKit leaderboard app
```
