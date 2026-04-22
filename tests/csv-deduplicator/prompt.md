# Company Record Deduplicator

## Goal

Build a Python module that identifies and merges duplicate company records in a
CSV file. Companies may appear multiple times with slightly different names,
addresses, or statuses.

## Input file

- `companies.csv` — 20 rows of UK company records with columns: `id`, `name`,
  `address`, `postcode`, `sic_code`, `status`.

## Matching rules

Two records are duplicates if they match on **both** of these criteria:

1. **Postcode match**: Identical `postcode` (case-insensitive).
2. **SIC code match**: Identical `sic_code`.

Records that share the same postcode AND sic_code are considered duplicates of
the same company, regardless of name or address variations.

## Merge rules

When merging a group of duplicates into one canonical record:

1. **id**: Use the lowest `id` in the group.
2. **name**: Use the longest `name` in the group (most complete version).
3. **address**: Use the longest `address` in the group.
4. **postcode**: Keep as-is (they're identical within a group).
5. **sic_code**: Keep as-is (they're identical within a group).
6. **status**: Use `"Active"` if ANY record in the group is `"Active"`,
   otherwise use the most common status.
7. **duplicate_count**: Add this column — the number of original records that
   were merged (1 if no duplicates found).

## Output

1. Save the deduplicated records to `output.csv`, sorted by `id` ascending.
   No row index.
2. Save a summary to `summary.json`:

```json
{
  "input_rows": 20,
  "output_rows": <number of deduplicated records>,
  "duplicates_found": <number of records that were part of a duplicate group>,
  "groups_merged": <number of groups that had more than 1 record>
}
```

## Requirements

- Write clean, modular Python code.
- The deduplication logic should be in a function, not inline script.
- Use pandas for data manipulation.
