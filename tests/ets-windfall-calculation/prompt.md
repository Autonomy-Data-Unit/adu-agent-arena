# ETS Windfall Calculation

You are given raw UK Emissions Trading Scheme (ETS) data files. Your task is to
merge them, compute emissions gaps and windfall profits, and produce an output
Excel workbook.

## Input files (in `data/`)

- **OHA allocation files** (4 files, one per year 2021-2024): Operator Holding
  Account allocations, named `uk_ets_Standard_Report_OHA_Participants_Allocations_{year}_*.xlsx`
- **AOHA allocation files** (4 files, one per year 2021-2024): Aircraft Operator
  Holding Account allocations, named `uk_ets_Standard_Report_AOHA_Participants_Allocations_{year}_*.xlsx`
- **Compliance report**: `20240607_Compliance_Report_Emissions_and_Surrenders.xlsx`
  (use the "Data" sheet)

## Task

1. **Merge OHA files**: Read all 4 OHA Excel files and merge them on their
   common columns to combine year-specific allocation data into a single
   dataframe.

2. **Merge AOHA files**: Do the same for the 4 AOHA Excel files.

3. **Combine OHA and AOHA**: Add an `Activity Type` column set to `'AVIATION'`
   for AOHA entries. Create a unified `Installation ID or Aircraft operator ID`
   column (from `Installation ID` for OHA rows, `Aircraft Operator ID` for AOHA
   rows). Outer-merge the two dataframes on their common columns.

4. **Merge compliance data**: Read the compliance report's "Data" sheet and
   left-merge it with the combined dataframe on common columns.

5. **Clean data**: In the `Recorded emissions` columns for 2021-2023, replace
   the string value `'EXCLUDED'` with null.

6. **Compute emissions gaps** (for 2021, 2022, 2023):
   `Emissions gap {year} = Recorded emissions {year} - Allocation Delivered_{year}`

7. **Compute total allocation costs** (for 2021, 2022, 2023, 2024):
   `Total allocation cost {year} = Allocation Delivered_{year} * carbon_price_{year}`
   Using these annual average carbon prices (GBP per tCO2e):
   - 2021: 55.56
   - 2022: 79.20
   - 2023: 55.44
   - 2024: 35.00

8. **Compute windfall values** (for 2021, 2022, 2023 only):
   `Windfall {year} = Emissions gap {year} * carbon_price_{year}`

9. **Create "By installation" sheet**: Sort rows by `Account Holder Name`
   ascending.

10. **Create "By company" sheet**: Group the installation-level data by
    `Account Holder Name`, summing all numeric columns. Drop the columns
    `Installation ID`, `First Year of Operation`,
    `Installation ID or Aircraft operator ID`, `Aircraft Operator ID`,
    `Last Year of Operation`, and `NACE Code` (these are meaningless when
    summed). Sort by `Account Holder Name`.

11. **Save output**: Write both sheets to `output/ETS_windfalls.xlsx` with
    sheet names `By installation` and `By company`. Do not include the
    dataframe index.

## Expected output columns

### "By installation" sheet (45 columns):
Account Holder Name, Installation ID or Aircraft operator ID, Installation ID,
Installation name, Permit ID, Aircraft Operator ID, Monitoring plan ID,
Permit ID or Monitoring plan ID, Sales Contact Email, Sales Contact Phone,
Installation Name, Activity Type, Regulator, Account type, Account status,
NACE Code, NACE Description, First Year of Operation, Last Year of Operation,
Static surrender status 2021, Static surrender status 2022,
Static surrender status 2023, Recorded emissions 2021,
Recorded emissions 2022, Recorded emissions 2023, Cumulative emissions,
Cumulative surrenders, Allocation Entitlement_2021,
Allocation Entitlement_2022, Allocation Entitlement_2023,
Allocation Entitlement_2024, Allocation Delivered_2021,
Allocation Delivered_2022, Allocation Delivered_2023,
Allocation Delivered_2024, Emissions gap 2021, Emissions gap 2022,
Emissions gap 2023, Total allocation cost 2021, Total allocation cost 2022,
Total allocation cost 2023, Total allocation cost 2024, Windfall 2021,
Windfall 2022, Windfall 2023

### "By company" sheet (24 columns):
Account Holder Name, Recorded emissions 2021, Recorded emissions 2022,
Recorded emissions 2023, Cumulative emissions, Cumulative surrenders,
Allocation Entitlement_2021, Allocation Entitlement_2022,
Allocation Entitlement_2023, Allocation Entitlement_2024,
Allocation Delivered_2021, Allocation Delivered_2022,
Allocation Delivered_2023, Allocation Delivered_2024, Emissions gap 2021,
Emissions gap 2022, Emissions gap 2023, Total allocation cost 2021,
Total allocation cost 2022, Total allocation cost 2023,
Total allocation cost 2024, Windfall 2021, Windfall 2022, Windfall 2023
