# Climate Price Impact Calculator

**Archetype:** `notebook-analysis`
**Inspired by:** [food_foundation_climate_shock](https://github.com/Autonomy-Data-Unit/food_foundation_climate_shock) -- estimating retail food price impacts under climate change scenarios.

## Task

Estimate the retail price impact of climate change on 20 UK fruit and vegetable
items under 2°C and 4°C warming scenarios, using a three-channel economic model:
domestic yield shocks, import-weighted yield shocks, and glasshouse energy savings.

## What the agent must do

1. Load four input CSVs (trade map, domestic yields, import yields, glasshouse energy)
2. Look up beta pass-through coefficients by COICOP category (fruit vs vegetables)
3. Compute the domestic yield impact channel for each item and scenario
4. Compute the import-weighted yield impact by joining trade shares with country-level yield deltas
5. Compute glasshouse energy savings for applicable items (negative price effect)
6. Sum the three channels to produce a total percentage price change per item
7. Produce a summary with descriptive statistics

## Key files

- [prompt.md](prompt.md) -- Task specification with full formula
- [dataset.json](dataset.json) -- Scoring configuration
- [Task code](../../src/adu_arena/tasks/climate_price.py)
- [Deterministic scorer](../../src/adu_arena/scorers/deterministic.py) | [Judge scorer](../../src/adu_arena/scorers/judge.py)

## Deterministic checks

- `price_impact.csv` and `summary.json` exist
- CSV schema matches expected 12 columns
- Exactly 20 rows
- Median 2°C price impact within tolerance
- Mean 4°C price impact within tolerance
- Summary JSON contains expected keys and item count

## Why this test matters

Multi-channel economic modelling from documented formulas is a common ADU
analysis pattern. This test evaluates whether an agent can correctly implement
a non-trivial formula from prose, join multiple data sources on composite keys,
handle sign conventions (yield losses cause price increases), and correctly
differentiate between item categories (glasshouse vs non-glasshouse, fruit vs
vegetable beta coefficients).
