# ADU Agent Arena — Plan

## Mission

Benchmark coding agents on the kind of data-led research the Autonomy Data Unit actually does — scraping (Companies House, ONS, etc.), data pipelines, and Jupyter-based analysis. Tests are drawn from real ADU project patterns rather than generic SWE benchmarks.

**Agent-under-test:** `pi-coding-agent` from [pi-mono](https://github.com/badlogic/pi-mono). The "agents" we benchmark are pi-coding-agent instantiated across a matrix of model/provider configurations (e.g. `pi + claude-opus-4-7`, `pi + gpt-5`, `pi + gemini-2.5-pro`). Each configuration is a separate entrant on the leaderboard.

**Foundation:** Built on [Inspect AI](https://inspect.aisi.org.uk/) (UK AISI's evaluation framework) rather than a from-scratch harness. Inspect provides sandboxing, scoring, logging, budget enforcement, and agent bridging. We write the ADU-specific tasks, scorers, and leaderboard on top.

---

## Why Inspect AI

We surveyed the landscape (SWE-bench, OpenHands, HAL, DPAI Arena, KramaBench, DSBench, etc.). Nothing targets our domain (UK public-data scraping + pipelines + notebook analysis) or supports plugging in pi-coding-agent. Building a custom harness would mean reimplementing sandboxing, scoring, logging, budget enforcement, and agent orchestration — all of which Inspect already does well.

**What Inspect gives us for free:**
- Docker-sandboxed per-sample execution
- `sandbox_agent_bridge()` — purpose-built for CLI agents like pi-coding-agent running inside containers, with automatic API call proxying and token/cost tracking
- Custom deterministic scorers with sandbox filesystem access
- Built-in LLM-judge scorers (`model_graded_qa`) with custom rubric templates
- Budget enforcement: `time_limit`, `token_limit`, `cost_limit` per sample
- `eval_set()` for running tasks across a model matrix with retry and sample preservation
- `evals_df()` / `samples_df()` for Pandas-based result analysis
- Structured log storage (`.eval` files) with CLI tools (`inspect log list`, `inspect log dump`)
- Built-in log viewer (`inspect view`)

**What we build on top:**
- Pi-coding-agent solver (thin adapter using `sandbox_agent_bridge`)
- ADU task definitions (Python `@task` functions)
- Deterministic scorers for our archetypes (CSV schema, row counts, numeric checks, file existence)
- LLM-judge rubrics per archetype
- SvelteKit leaderboard consuming Inspect's log output
- `export_leaderboard.py` script to transform logs → leaderboard JSON

---

## Pi-coding-agent integration

Pi-mono exposes several invocation modes. For the arena, we use **print mode** inside a Docker sandbox:

```bash
cd /workspace && \
  pi -p \
     --no-session \
     --no-extensions \
     --no-skills \
     --no-context-files \
     --no-prompt-templates \
     --provider anthropic \
     --model claude-sonnet-4-20250514 \
     --tools read,bash,edit,write \
     "Your task prompt here"
```

This is wrapped as an Inspect solver using `sandbox_agent_bridge()`, which intercepts pi's model API calls and routes them through Inspect's provider layer — giving us automatic token/cost tracking without pi needing to know about Inspect.

**Configuration axes for the agent matrix:**
- Provider (anthropic, openai, google, etc.)
- Model ID
- Thinking level (off, minimal, low, medium, high, xhigh)
- Tool set (default vs restricted)

Each unique combination is a separate leaderboard entrant.

---

## Repository structure

```
adu-agent-arena/
├── pyproject.toml                  # depends on inspect-ai, pandas, etc.
├── src/adu_arena/
│   ├── agents/
│   │   └── pi_agent.py             # pi-coding-agent solver
│   ├── scorers/
│   │   ├── deterministic.py        # CSV schema, row counts, file checks, numeric
│   │   └── judge.py                # LLM-judge rubric templates per archetype
│   └── tasks/                      # one module per test
│       ├── ets_windfall.py
│       ├── care_consolidation.py
│       ├── ch_ixbrl_parser.py
│       └── ...
├── tests/                          # test assets (not Python tests)
│   └── <test-name>/
│       ├── dataset.json            # Inspect Sample(s): prompt, target, metadata
│       ├── workspace/              # files the agent starts with
│       ├── fixtures/               # golden outputs for scoring (never shown to agent)
│       └── compose.yaml            # per-test Docker Compose config
├── docker/
│   └── Dockerfile                  # base image: Python + data-science libs + pi-coding-agent
├── web/                            # SvelteKit leaderboard
├── scripts/
│   └── export_leaderboard.py       # reads Inspect logs → leaderboard.json
└── logs/                           # Inspect eval logs (gitignored)
```

---

## Test format

Each test is an Inspect `@task` function backed by a folder in `tests/<test-name>/`.

**`dataset.json`** — One or more `Sample` objects:
```json
[
  {
    "input": "contents of prompt.md or inline prompt",
    "target": "expected output description for scoring",
    "metadata": {
      "archetype": "pipeline-stage",
      "checks": {
        "expected_file": "/workspace/output.csv",
        "expected_columns": ["id", "name", "value"],
        "expected_row_count": 142,
        "numeric_checks": [
          {"column": "value", "aggregation": "sum", "expected": 12345.67, "tolerance": 0.01}
        ]
      }
    },
    "files": {
      "/workspace/input.csv": "workspace/input.csv"
    },
    "sandbox": ["docker", "compose.yaml"]
  }
]
```

**`workspace/`** — Starting files copied into the sandbox. This is all the agent sees.

**`fixtures/`** — Reference outputs for scoring. Never mounted in the sandbox.

**`compose.yaml`** — Docker Compose config for this test's sandbox. Most tests share the base image; tests needing extra services (e.g. Postgres) extend it.

---

## Test archetypes

Derived from surveying repos across the `Autonomy-Data-Unit` GitHub org.

### 1. `scrape-and-structure`
Agent is given target URLs/API docs + sample HTML/responses. Must write a scraper that fetches, parses, and outputs structured data (CSV/JSON). Network access may be required (allowlisted domains) or the agent works against frozen HTML fixtures.

### 2. `pipeline-stage`
Agent is given frozen intermediate data and a spec for the next transformation. Must produce a script/notebook that reads the input and writes the output. Purely deterministic — no network, no LLM calls needed.

### 3. `notebook-analysis`
Agent is given raw data files and an analytical question. Must produce a notebook or script that loads the data, performs analysis, and outputs results (tables, numbers, charts). Evaluation mixes deterministic checks (numeric answers) with LLM-judge (methodology quality).

### 4. `full-project-reproduction`
Agent is given a high-level spec and minimal scaffolding. Must produce a working module or pipeline from scratch. The hardest archetype — evaluates architecture, correctness, and code quality.

---

## Evaluation design

### Deterministic scorers (primary)
A reusable scorer driven by metadata in each `Sample`:

- **File existence** — expected output files exist in the sandbox
- **CSV schema** — column names match expected set
- **Row count** — exact match or within tolerance
- **Numeric checks** — aggregate values (sum, mean, min, max) within epsilon
- **Content checks** — specific strings present/absent in output
- **Hash checks** — sorted output matches a stable hash (for fully deterministic tasks)

These run inside the sandbox via `sandbox().exec()`, so they have access to pandas, etc.

### LLM-judge scorers (supplementary)
For qualitative aspects (code clarity, methodology, narrative quality). Uses Inspect's built-in `model_graded_qa()` with per-archetype rubric templates. The grading model is configurable (default: `claude-sonnet-4-20250514`).

Rubrics are kept minimal for now — we'll iterate after seeing a few real test runs. Initial rubric dimensions:
- Does the code produce correct output?
- Is the methodology sound?
- Is the code clean and readable?

### Reproducibility
Every run records: agent config (provider, model, thinking level, tools), prompt hash, workspace hash, Inspect version, scorer versions, wall-time, token count, cost.

---

## Budgets

Inspect's built-in limit system, configured per-task:

```python
@task
def my_task() -> Task:
    return Task(
        ...,
        time_limit=900,       # wall-clock seconds
        token_limit=500_000,  # total tokens
        cost_limit=5.00,      # USD
    )
```

When a limit trips, Inspect terminates the run gracefully and records which dimension was hit. Global caps are enforced by a wrapper that validates task configs at load time — no task can exceed the cap defined in a shared config module.

---

## Proposed initial tests

Derived from surveying 15 repos across the Autonomy-Data-Unit org. We picked 8 tests spanning all four archetypes, ranging from simple to medium complexity.

### 1. `ets-windfall-calculation` — notebook-analysis (Simple)
**Source:** `2024_10_emissions-trading-registry-analysis`

Agent receives raw UK ETS Excel files (OHA/AOHA allocations 2021–2024, compliance report) and a specification: merge participant data, join with compliance, compute emissions gaps and windfall profits using given annual carbon prices, produce an Excel with "By installation" and "By company" sheets.

**Evaluation:** Deterministic. Column names, row counts, and spot-check computed values for known installations against reference output.

### 2. `care-data-consolidation` — pipeline-stage (Simple–Medium)
**Source:** `care-visa-sponsorship-database`

Agent receives four raw care provider files (England/CQC, Scotland/CI, Wales/CIW, NI/RQIA) with different schemas plus a target unified 22-column schema. Must consolidate into a single CSV with correct column mappings, status normalization, and edge-case handling.

**Evaluation:** Deterministic. Row count = sum of inputs. Status values in {"Active", "Inactive"}. Country column has exactly four unique values. Column set matches spec.

### 3. `ch-ixbrl-parser` — full-project-reproduction (Medium)
**Source:** `ch-store`

Agent receives sample Companies House iXBRL/HTML filings and a spec: write a Python module that extracts company metadata from iXBRL tags, strips XBRL noise while preserving financial figures, and chunks the text. Three test files with known expected outputs provided.

**Evaluation:** Deterministic. Extracted company numbers match expected. Financial figures appear in output. XBRL noise strings absent. Chunk count and overlap correct.

### 4. `climate-food-inflation-blending` — pipeline-stage (Medium)
**Source:** `food_foundation_climate_shock`

Agent receives a trade map CSV, Comtrade import values, and country-level inflation projections. Must compute import-weighted international inflation per item, handle fallback items, blend domestic + international impacts, and produce a 20-row output table.

**Evaluation:** Deterministic. All 20 items present. Numeric values within 0.1pp tolerance. Fallback items correctly flagged. Import-only items handled correctly.

### 5. `contracts-finder-scraper` — scrape-and-structure (Medium)
**Source:** `corruption-tracker-dataset`

Agent receives Contracts Finder API docs and a Pydantic model spec. Must write an async scraper that searches for awarded contracts, handles pagination, validates responses, fetches full notice details, and saves as JSON.

**Evaluation:** Deterministic (Pydantic models validate against sample response) + LLM judge (code quality, error handling, rate limiting).

### 6. `donations-cleaning-pipeline` — pipeline-stage (Simple–Medium)
**Source:** `corruption-tracker-dataset`

Agent receives raw Electoral Commission donations CSV (~89K rows). Must filter to corporate donors, parse monetary values, tokenize donor names (strip common business suffixes), create Pydantic models, validate, and export as JSON.

**Evaluation:** Deterministic. Output contains only Company/LLP donors. Values are numeric. Tokenized names exclude specified common words. Pydantic validation passes.

### 7. `medrxiv-scraper` — scrape-and-structure (Simple)
**Source:** `medRxiv-abstract-scraper`

Agent receives sample medRxiv listing and article HTML pages. Must write an async scraper that extracts titles, authors, links, and abstracts. Works against frozen HTML fixtures (no network needed).

**Evaluation:** Deterministic. Parsed fields match expected strings from sample pages. CSV has correct columns and row count. Async implementation present.

### 8. `entity-sic-resolution` — pipeline-stage (Medium)
**Source:** `spotlight-on-corruption_ministerial-meetings-sic-coding`

Agent receives 50 entity names from ministerial meeting disclosures, Companies House Search API access, and an LLM for disambiguation. Must search, disambiguate, retrieve SIC codes, and store structured results.

**Evaluation:** Deterministic spot-checks (known company numbers) + LLM judge (matching quality). At least 70% correct matches against reference key.

### Test summary

| Test | Archetype | Complexity | Evaluation |
|---|---|---|---|
| `ets-windfall-calculation` | notebook-analysis | Simple | Deterministic |
| `care-data-consolidation` | pipeline-stage | Simple–Medium | Deterministic |
| `ch-ixbrl-parser` | full-project-reproduction | Medium | Deterministic |
| `climate-food-inflation-blending` | pipeline-stage | Medium | Deterministic |
| `contracts-finder-scraper` | scrape-and-structure | Medium | Det. + LLM judge |
| `donations-cleaning-pipeline` | pipeline-stage | Simple–Medium | Deterministic |
| `medrxiv-scraper` | scrape-and-structure | Simple | Deterministic |
| `entity-sic-resolution` | pipeline-stage | Medium | Det. + LLM judge |

---

## Stack

- **Evaluation framework:** Inspect AI
- **Sandboxing:** Docker (via Inspect's Docker sandbox)
- **Language:** Python for everything except the leaderboard
- **Package management:** uv
- **Leaderboard:** SvelteKit static site reading `leaderboard.json`
- **Agent:** pi-coding-agent (npm package `@mariozechner/pi-coding-agent`)

---

## Leaderboard

SvelteKit static site reading JSON exported from Inspect's logs.

`scripts/export_leaderboard.py` uses `evals_df()` and `samples_df()` to:
- Aggregate scores per agent config (mean, pass rate, cost/time distributions)
- Track trends over time (every eval log has a timestamp)
- Export per-test and per-agent views

The web app shows:
- Per-test pass/fail by agent config
- Per-agent aggregate scores
- Trend view over time for a given agent config
- Cost and time tracking
- Drill-down into individual runs

---

## What we are NOT building

Things the original plan included that Inspect already handles:

- Custom CLI framework (`arena run`, `arena list`, etc.) — use `inspect eval`, `inspect eval-set`, `inspect view`
- Custom TOML config schemas (arena.toml, test.toml) — tasks are Python `@task` functions with parameters
- Custom result storage format — Inspect's `.eval` log files + `evals_df()`
- Custom budget enforcement — Inspect's `time_limit`, `token_limit`, `cost_limit`
- Custom sandbox orchestration — Inspect's Docker sandbox
- Custom agent adapter interface — `sandbox_agent_bridge()`

---

## Open questions

1. **Podman compatibility** — We're using Docker. If we later want Podman, Inspect calls the `docker` CLI directly, so `podman-docker` aliasing should work but isn't officially tested.
2. **Pi's own API keys vs Inspect's bridge** — The bridge proxies API calls through Inspect's provider, giving us token/cost tracking. But pi might behave differently with proxied vs direct API keys. Need to test.
3. **Network access for scraping tests** — Tests like `contracts-finder-scraper` and `entity-sic-resolution` need real API access. We can either use frozen fixtures (simpler, reproducible) or allowlist specific domains in the Docker network config. Start with fixtures, graduate to live APIs later.
4. **Judge model consistency** — Using a fixed judge model version for reproducibility, or always latest? Start with a pinned version.
5. **Pi version pinning** — Pin the pi-coding-agent version in the Docker image for reproducibility. Update deliberately.

---

## Phase 1 — Implementation sequence

Once this plan is approved:

1. Python package scaffolding (`pyproject.toml`, `src/adu_arena/`, uv setup)
2. Base Docker image (Python + data-science libs + pi-coding-agent + Node.js)
3. Pi-coding-agent solver (`sandbox_agent_bridge` integration)
4. Reusable deterministic scorer (driven by sample metadata)
5. First test: `ets-windfall-calculation` (simplest, fully deterministic)
6. Second test: `medrxiv-scraper` (simple, different archetype)
7. LLM-judge scorer with initial rubric
8. Third test: `contracts-finder-scraper` (first test using LLM judge)
9. `export_leaderboard.py` script
10. Minimal SvelteKit leaderboard
11. Remaining tests
