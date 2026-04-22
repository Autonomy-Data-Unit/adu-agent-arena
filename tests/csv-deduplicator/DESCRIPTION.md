# CSV Deduplicator

**Archetype:** full-project-reproduction
**Data:** Synthetic company records modelled on Companies House data

## Task

Build a Python module that identifies and merges duplicate company records using postcode + SIC code matching, with specific merge rules for resolving conflicts.

## What the agent must do

1. Read a 20-row CSV of company records with known duplicates
2. Implement matching logic: group by (postcode, sic_code)
3. Apply merge rules for each field:
   - Lowest ID, longest name, longest address
   - "Active" status wins over other statuses
   - Count duplicates per group
4. Write clean, modular code (function-based, not inline script)
5. Produce a deduplicated CSV (11 rows) and summary JSON

## Deterministic checks

- Output CSV exists with correct schema (7 columns)
- Exactly 11 output rows
- Summary JSON: 7 groups merged, 16 records involved in duplicates

## Why this test matters

Tests the agent's ability to build a complete, working module from a specification. Requires understanding groupby operations, conflict resolution logic, and producing well-structured code. The "full-project-reproduction" archetype — not just transforming data, but writing a reusable tool.
