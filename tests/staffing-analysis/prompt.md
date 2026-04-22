# Local Authority Staffing Analysis

## Goal

Analyse local authority staffing data to compare South Cambridgeshire District
Council's workforce metrics against all other English Shire Districts.

## Input files

- `QPSES 2024 Q1.xlsx` — Quarterly Public Sector Employment Survey. Sheet
  "Final Individual" contains staffing headcounts for all English & Welsh local
  authorities. Key columns: `Auth Name`, `Type`, `Total Headcount`,
  `Temporary/Casual`.
- `nomis.csv` — Mid-year population estimates for local authority districts.
  Columns: `lad` (authority name), `population` (integer).

## Task

Write a Python script that produces `output.csv` with one row per Shire District
and the following columns:

1. **Filter**: Keep only rows where `Type == "Shire District"` from the QPSES
   data. Then exclude the 6 former Cumbrian districts that were merged into
   unitary authorities in 2023 (they have no matching population data):
   `Allerdale`, `Barrow-in-Furness`, `Carlisle`, `Copeland`, `Eden`,
   `South Lakeland`. This should leave 164 authorities.

2. **Merge**: Join with `nomis.csv` on authority name. Note: NOMIS uses
   "Folkestone and Hythe" where QPSES uses "Shepway" — rename to match before
   merging.

3. **Compute**: Add a column `employees_per_1000` = 1000 * `Total Headcount` /
   `population`.

4. **Compute**: Add a column `temp_casual_pct` = 100 * `Temporary/Casual` /
   `Total Headcount`. Rows where both values are 0 will produce NaN — leave
   them as NaN.

5. **Output columns**: `Auth Name`, `population`, `Total Headcount`,
   `employees_per_1000`, `Temporary/Casual`, `temp_casual_pct`.

6. **Sort** by `Auth Name` ascending.

7. **Save** to `output.csv` with no row index.

## Expected summary statistics

After generating the output, also create `summary.json` containing:

```json
{
  "n_districts": <number of rows>,
  "south_cambs_employees_per_1000": <South Cambridgeshire's rate>,
  "median_employees_per_1000": <median of all districts>,
  "q1_employees_per_1000": <25th percentile>,
  "q3_employees_per_1000": <75th percentile>,
  "south_cambs_temp_casual_pct": <South Cambridgeshire's temp/casual %>,
  "median_temp_casual_pct": <median, excluding NaN rows>
}
```

Round all values to 4 decimal places.
