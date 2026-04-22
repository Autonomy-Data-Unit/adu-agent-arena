# Government Contracts Scraper

**Archetype:** scrape-and-structure
**Data:** Synthetic HTML modelled on Crown Commercial Service contract listings

## Task

Parse a realistic HTML page containing 8 UK government contract awards and extract structured data into a CSV with computed fields.

## What the agent must do

1. Parse HTML using BeautifulSoup or equivalent
2. Extract 8 fields per contract from nested `<dl>` elements
3. Parse monetary values (strip `£` and commas, convert to integer)
4. Parse dates from DD/MM/YYYY to YYYY-MM-DD format
5. Compute contract duration in days
6. Handle HTML entities (`&amp;` in organisation names)
7. Produce a sorted CSV and summary JSON with aggregate statistics

## Deterministic checks

- Output CSV exists with correct schema (9 columns)
- 8 rows (one per contract)
- Summary JSON contains correct total value (£68,490,500)
- Correct top organisation and supplier identified

## Why this test matters

HTML scraping and data structuring is core ADU work. This test uses clean, unambiguous HTML so the "correct" parse is deterministic, while still requiring the agent to handle real-world patterns: monetary parsing, date format conversion, HTML entity decoding, and computed fields.
