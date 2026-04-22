# Culture Spending Analysis

**Archetype:** notebook-analysis
**Source:** [equity-local-authority-culture-spending](https://github.com/Autonomy-Data-Unit/equity-local-authority-culture-spending)

## Task

Analyse 15 years of UK local authority culture spending data (5,501 rows covering England, Scotland, and Wales) to answer four specific analytical questions.

## What the agent must do

1. Load a large CSV with 14 columns of spending data
2. Answer four questions requiring filtering, aggregation, and comparison:
   - Which LA had the highest real-terms spending in 2024?
   - How many LAs reported zero nominal spending in 2024?
   - What is the total English real-terms spending in 2023?
   - How many English LAs spent more in 2024 than 2010?
3. Output answers as structured JSON

## Deterministic checks

- Output JSON exists
- Contains the correct top spender ("City of London")
- Contains all four answer keys

## Why this test matters

Tests the agent's ability to work with a moderately large dataset, apply correct filtering logic across multiple dimensions (country, year), and produce precise numerical answers. A common ADU task pattern: "here's the data, answer these questions."
