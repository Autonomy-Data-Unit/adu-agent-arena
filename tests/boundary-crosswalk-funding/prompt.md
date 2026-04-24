# Boundary Crosswalk Funding Harmonisation

## Goal

Harmonise arts funding data from three UK countries onto a single set of 2024
parliamentary constituency boundaries (PCON24), then adjust all values for
inflation using CPI data.

## Input files

- `england_funding.csv` -- Funding per constituency using PCON16 boundaries.
  Columns: `constituency`, then fiscal year headers (`2016/17`, `2017/18`, ...,
  `2022/23`). Values are in GBP.

- `wales_funding.csv` -- Funding per constituency using PCON05 boundaries.
  Columns: `constituency`, then calendar year headers (`2016`, `2017`, ...,
  `2023`). Uses `-` for missing values. Includes an "Outside Wales" row that
  should be excluded from the output.

- `ni_funding.csv` -- Funding per constituency using PCON10 boundaries.
  Columns: `constituency`, then calendar year headers (`2016`, ..., `2023`).
  Constituency names are in UPPERCASE and do not match PCON24 names directly.
  Uses `-` for missing values.

- `crosswalk_england.csv` -- Maps old PCON16 constituencies to PCON24. Columns:
  `pcon24`, `old_constituency`, `share` (fraction of old constituency's funding
  that goes to the new one, between 0 and 1).

- `crosswalk_wales.csv` -- Same format, maps PCON05 to PCON24.

- `ni_name_mapping.csv` -- Maps NI raw names to PCON24 names. Columns:
  `raw_name`, `pcon24`. NI constituencies are 1:1 (no splitting).

- `cpi_december.csv` -- ONS CPI index values (December) for 2016-2023.
  Columns: `year`, `cpi_index`.

- `pcon24_reference.csv` -- All PCON24 constituencies and their country.
  Columns: `pcon24`, `country`.

## Task

Write a Python script that produces `output.csv`:

1. **Parse England data**: Read `england_funding.csv`. Convert fiscal year
   headers to calendar years by taking the first year (e.g. `2016/17` becomes
   `2016`). This gives years 2016-2022.

2. **Parse Wales data**: Read `wales_funding.csv`. Replace `-` values with 0.
   Exclude the "Outside Wales" row.

3. **Parse NI data**: Read `ni_funding.csv`. Replace `-` values with 0. Map
   constituency names to PCON24 using `ni_name_mapping.csv`.

4. **Apply England crosswalk**: For each PCON24 constituency, compute its
   funding as `sum(old_value * share)` across all old constituencies that
   contribute to it, using `crosswalk_england.csv`. Note: some old
   constituencies split across multiple PCON24 constituencies.

5. **Apply Wales crosswalk**: Same logic using `crosswalk_wales.csv`.

6. **NI mapping**: NI is 1:1, so just rename using the mapping.

7. **Combine**: Merge all three countries into a single table with one row per
   PCON24 constituency. The unified year range is 2016-2023. England has no
   2023 data -- fill with 0.

8. **Inflation adjustment**: Using `cpi_december.csv`, compute inflation-adjusted
   values for each year. The base year is 2023. For each year, the adjusted
   value is: `nominal_value * (cpi_2023 / cpi_year)`. Create columns named
   `{year}_infadj` (e.g. `2016_infadj`, `2017_infadj`, ..., `2023_infadj`).

9. **Output columns**: `pcon24`, `country`, `2016`, `2017`, `2018`, `2019`,
   `2020`, `2021`, `2022`, `2023`, `2016_infadj`, `2017_infadj`,
   `2018_infadj`, `2019_infadj`, `2020_infadj`, `2021_infadj`, `2022_infadj`,
   `2023_infadj`.

10. **Sort** by `pcon24` ascending. Round all numeric values to 2 decimal
    places. Save to `output.csv` with no row index.

## Validation

After generating the output, also create `validation.json` containing:

```json
{
  "total_constituencies": <number of rows>,
  "england_total_nominal": <sum of all England nominal values across all years>,
  "wales_total_nominal": <sum of all Wales nominal values across all years>,
  "ni_total_nominal": <sum of all NI nominal values across all years>,
  "median_2022_nominal": <median of the 2022 column across all constituencies>,
  "conservation_check": <ratio of England output total to England input total, should be ~1.0>
}
```

Round all values to 2 decimal places except `conservation_check` (6 decimal places).
