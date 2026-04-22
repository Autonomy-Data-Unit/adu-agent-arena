# medRxiv Article Scraper

## Goal

Write a Python script that parses frozen HTML pages from the medRxiv preprint server
and extracts article metadata into a CSV file.

The HTML fixtures simulate two types of pages from medRxiv:

1. **Listing page** (`sample_listing.html`) -- contains a list of article citations
2. **Article pages** (`article_1.html`, `article_2.html`, `article_3.html`) -- each
   contains the full abstract for one article

## Input files

All input files are in the current working directory:

- `sample_listing.html` -- a medRxiv listing/search-results page containing 3 article entries
- `article_1.html` -- individual article page for the 1st listed article
- `article_2.html` -- individual article page for the 2nd listed article
- `article_3.html` -- individual article page for the 3rd listed article

## Requirements

1. Parse `sample_listing.html` to extract each article's:
   - **title** -- the text content of the article's title link
   - **link** -- the full URL to the article (combine the base URL `https://www.medrxiv.org`
     with the relative href from the listing page)
   - **authors** -- the text content of the authors span

2. For each article found in the listing, parse the corresponding article page
   (`article_1.html`, `article_2.html`, `article_3.html` -- matched by order)
   to extract:
   - **abstract** -- the text content of the first `<p>` inside the abstract section

3. Combine all extracted data and save to `output.csv` with columns:
   `title`, `link`, `authors`, `abstract`

4. The CSV must NOT include a row-index column.

## Hints

- The HTML uses the [Highwire Press](https://www.highwirepress.com/) platform markup.
  Relevant CSS classes include:
  - `highwire-article-citation` -- wraps each article entry on the listing page
  - `highwire-cite-title` -- contains the title; the title text is inside an `<a>` tag
  - `highwire-citation-authors` -- contains the authors text
  - `abstract` -- the abstract section on the article page; the abstract text is in the
    first `<p>` child element
- Use BeautifulSoup (or any HTML parser) to parse the files.
- Normalize author whitespace (collapse runs of whitespace into single spaces).

## Output

Save the result to `output.csv` in the current working directory.
