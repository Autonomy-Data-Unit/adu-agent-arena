# Government Contract Awards Scraper

## Goal

Parse an HTML page listing UK government contract awards and extract structured
data into a CSV file.

## Input file

- `contracts.html` — An HTML page containing 8 contract award listings from
  Crown Commercial Service.

## Task

Write a Python script that:

1. **Parse** `contracts.html` using BeautifulSoup or any HTML parser.

2. **Extract** from each `.search-result` element:
   - `contract_id`: from the `data-contract-id` attribute
   - `title`: text content of the `.search-result-title a` element
   - `organisation`: text content of the `.organisation` element
   - `supplier`: text content of the `.supplier` element
   - `value_gbp`: parsed from the `.value` element — remove the `£` sign and
     commas, convert to integer
   - `award_date`: from the `.award-date` element, parsed to YYYY-MM-DD format
   - `start_date`: from the `.start-date` element, parsed to YYYY-MM-DD format
   - `end_date`: from the `.end-date` element, parsed to YYYY-MM-DD format
   - `duration_days`: computed as (end_date - start_date) in days

3. **Save** to `output.csv` sorted by `award_date` ascending. No row index.

4. **Save** summary statistics to `summary.json`:

```json
{
  "total_contracts": 8,
  "total_value_gbp": <sum of all value_gbp>,
  "avg_value_gbp": <mean of all value_gbp>,
  "avg_duration_days": <mean of all duration_days, rounded to 1 decimal>,
  "top_organisation": "<organisation with highest total spend>",
  "top_supplier": "<supplier with highest single contract value>"
}
```

## Notes

- HTML entities like `&amp;` should be decoded (e.g. `&amp;` → `&`).
- Dates in the HTML are in DD/MM/YYYY format.
