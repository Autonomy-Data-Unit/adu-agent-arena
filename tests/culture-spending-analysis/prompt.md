# UK Local Authority Culture Spending Analysis

## Goal

Analyse UK local authority culture spending data (2010–2024) to answer specific
analytical questions. The data covers England, Scotland, and Wales.

## Input file

- `final_output.csv` — 5,501 rows, one per local authority per year. Key columns:
  - `country`: England, Scotland, or Wales
  - `la_name`: Local authority name
  - `year`: 2010–2024
  - `spend_total_real`: Total culture spending in real terms (GBP)
  - `spend_net_real`: Net culture spending in real terms (total minus income)

## Task

Write a Python script that computes the answers to these questions and saves
the results to `answers.json`:

### Q1: Highest spender in 2024
Which local authority had the highest `spend_total_real` in 2024? Report the
`la_name` and the value.

### Q2: Zero spenders in 2024
How many local authorities reported exactly zero `spend_total` (the nominal
column, not real) in 2024?

### Q3: Total English spending in 2023
What is the sum of `spend_total_real` across all local authorities where
`country == "England"` and `year == 2023`?

### Q4: English LAs with higher spending in 2024 than 2010
How many English local authorities had strictly higher `spend_total_real` in
2024 than in 2010? Only count LAs present in both years.

## Output format

Save `answers.json` with this structure:

```json
{
  "q1_la_name": "<name>",
  "q1_value": <number>,
  "q2_count": <integer>,
  "q3_total": <number rounded to 2 decimal places>,
  "q4_count": <integer>
}
```
