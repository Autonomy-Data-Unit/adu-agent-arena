# Staffing Analysis

**Archetype:** pipeline-stage
**Source:** [public-sector-shorter-week](https://github.com/Autonomy-Data-Unit/public-sector-shorter-week)

## Task

Merge QPSES staffing headcount data with NOMIS population estimates for English Shire Districts, then compute per-capita employment rates and temporary/casual staff percentages.

## What the agent must do

1. Load an Excel file (QPSES) and a CSV (NOMIS population)
2. Filter to Shire Districts only, excluding 6 merged Cumbrian districts
3. Handle a name mismatch ("Folkestone and Hythe" vs "Shepway")
4. Merge the two datasets on authority name
5. Compute `employees_per_1000` and `temp_casual_pct`
6. Produce a sorted CSV and a JSON summary with median/quartile statistics

## Deterministic checks

- Output CSV exists with correct schema (6 columns)
- 164 rows (one per Shire District)
- Median of `employees_per_1000` within tolerance of 3.55
- Summary JSON contains expected keys and district count

## Why this test matters

This is a typical ADU data pipeline: two messy public datasets with schema mismatches that need cleaning, merging, and summarising. Tests the agent's ability to handle real-world data wrangling.
