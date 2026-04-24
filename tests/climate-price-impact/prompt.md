# Climate Price Impact Calculator

## Goal

Estimate the retail price impact of climate change on 20 priority UK fruit and
vegetable items under 2°C and 4°C warming scenarios. The model has three
channels that affect prices: domestic yield changes, import-weighted yield
changes, and glasshouse energy savings.

## Input files

- `trade_map.csv` -- UK trade profile for each item. Columns: `item`, `coicop`
  (COICOP classification code), `uk_prod_share` (fraction of UK consumption
  that is domestically produced, 0-1), `import_country_1`, `import_share_1`,
  `import_country_2`, `import_share_2`, `import_country_3`, `import_share_3`
  (top 3 import sources and their shares of total imports, summing to 1.0).

- `domestic_yields.csv` -- Projected UK yield changes from climate models.
  Columns: `item`, `gaez_crop` (GAEZ crop proxy used), `uk_yield_delta_2C`,
  `uk_yield_delta_4C` (fractional yield changes, e.g. -0.10 means a 10% yield
  loss). Glasshouse items and items with 0% UK production have 0.0 deltas.

- `import_yields.csv` -- Projected yield changes in import source countries.
  Columns: `item`, `country`, `import_yield_delta_2C`,
  `import_yield_delta_4C` (fractional yield changes, same convention as above).

- `glass_energy.csv` -- Glasshouse energy cost savings from warmer temperatures.
  Columns: `item`, `energy_retail_share` (fraction of retail price attributable
  to heating energy), `heating_reduction_2C` (fractional reduction in heating
  demand at 2°C, e.g. 0.17 = 17% less heating), `heating_reduction_4C`.
  Only contains rows for glasshouse items.

## Price impact formula

For each item, compute the price change as a percentage using three channels:

### Channel 1: Domestic yield impact

```
domestic_impact = -(uk_prod_share × uk_yield_delta × beta)
```

A yield loss (negative delta) produces a price increase (positive impact).

### Channel 2: Import yield impact

```
import_impact = -SUM over countries( import_share_j × (1 - uk_prod_share) × import_yield_delta_j × beta )
```

Same sign logic: yield losses in exporting countries raise UK import prices.

### Channel 3: Glasshouse energy savings (glasshouse items only)

```
energy_impact = -(uk_prod_share × energy_retail_share × heating_reduction)
```

Warmer temperatures reduce heating costs, which reduces prices (negative
impact). This channel is 0 for non-glasshouse items.

### Beta pass-through coefficients

The `beta` coefficient converts supply-side shocks to retail price changes.
It varies by COICOP category:

- Fruit (`01.1.6`): beta = **0.100**
- Vegetables (`01.1.7`): beta = **0.115**

### Total price change

```
delta_price_pct = (domestic_impact + import_impact + energy_impact) × 100
```

The result is expressed as a percentage change in retail price.

## Task

Write a Python script that:

1. Load all four input CSVs.

2. For each of the 20 items, compute the three impact channels for both the
   2°C and 4°C scenarios using the formulas above. Look up the `beta`
   coefficient from the item's `coicop` code.

3. Produce `price_impact.csv` with the following columns:
   - `item`
   - `coicop`
   - `beta`
   - `uk_prod_share`
   - `domestic_impact_2C` (the raw fractional domestic impact, not percentage)
   - `domestic_impact_4C`
   - `import_impact_2C`
   - `import_impact_4C`
   - `energy_impact_2C` (0 for non-glasshouse items)
   - `energy_impact_4C`
   - `delta_price_2C_pct` (total price change as a percentage)
   - `delta_price_4C_pct`

   Sort by `item` ascending. Round fractional impact columns to 6 decimal
   places and percentage columns to 4 decimal places. Save with no row index.

4. Produce `summary.json` containing:

```json
{
  "n_items": 20,
  "median_delta_price_2C_pct": <median of delta_price_2C_pct>,
  "mean_delta_price_4C_pct": <mean of delta_price_4C_pct>,
  "n_positive_2C": <count of items with positive delta_price_2C_pct>,
  "n_negative_2C": <count of items with negative delta_price_2C_pct>,
  "most_affected_item": "<item with highest delta_price_4C_pct>",
  "least_affected_item": "<item with lowest delta_price_4C_pct>"
}
```

Round numeric values to 4 decimal places.
