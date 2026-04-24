# Boundary Crosswalk Funding Harmonisation

**Archetype:** `pipeline-stage`
**Inspired by:** [equity-arts-funding](https://github.com/Autonomy-Data-Unit/equity-arts-funding) -- harmonising UK arts funding data across different constituency boundary vintages.

## Task

Harmonise arts funding data from three UK countries -- each reported against
different historical constituency boundaries and with different data schemas --
onto a single PCON24 geography, then inflation-adjust using CPI data.

## What the agent must do

1. Parse three differently-structured CSV files (fiscal years vs calendar years, `-` as missing values, uppercase names)
2. Convert England's fiscal year headers (`2016/17`) to calendar years (`2016`)
3. Apply area-weighted crosswalk matrices to redistribute funding from old boundaries to new PCON24 boundaries
4. Map Northern Ireland constituency names using a lookup table
5. Combine all three countries into a unified table with consistent year columns
6. Compute inflation-adjusted values using CPI data (2023 base year)
7. Produce validation statistics including a conservation-of-totals check

## Key files

- [prompt.md](prompt.md) -- Task specification
- [dataset.json](dataset.json) -- Scoring configuration
- [Task code](../../src/adu_arena/tasks/boundary_crosswalk.py)
- [Deterministic scorer](../../src/adu_arena/scorers/deterministic.py) | [Judge scorer](../../src/adu_arena/scorers/judge.py)

## Deterministic checks

- `output.csv` and `validation.json` exist
- CSV schema matches expected 18 columns
- Exactly 50 rows (30 England + 12 Wales + 8 NI)
- Median nominal 2022 funding within tolerance
- Median inflation-adjusted 2020 funding within tolerance
- Validation JSON contains expected keys and constituency count

## Why this test matters

Multi-source data harmonisation across different geographic boundary vintages is
a core ADU workflow. This test evaluates whether an agent can correctly handle
heterogeneous input schemas, apply crosswalk redistribution logic, and sequence
inflation adjustment -- skills essential for real-world policy data analysis.
