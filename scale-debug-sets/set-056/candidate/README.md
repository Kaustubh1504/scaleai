# Supplier Catalog Merge

Two suppliers send product feeds as CSV files. This tool validates every row, rejects the
rows it cannot use (with a reason code), merges the rest into one record per SKU, and
builds a per-category stock summary for the merchandising team.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/feeds/*.csv`: one file per supplier, processed in filename order. The file stem
  (`supplier_a`) is the row's `source`. Columns: `sku`, `title`, `category`, `price`,
  `qty`, `updated_at`, `status`. Header names may differ in case. Some suppliers export
  from Excel, so a file may start with a UTF-8 byte-order mark.
- `data/categories.json`: the category registry (`code`, `name`, `active`).

Line numbers count the header as line 1, so the first data row is line 2.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- All cells are trimmed. SKUs are upper-cased (` hm-100 ` → `HM-100`). Category codes
  are lower-cased, both in the feeds and in the registry.
- Registry `active` may be a JSON boolean, a number, or a string; as a string, `true`,
  `yes`, `y` and `1` (any case) mean active. A missing `active` means active.
- `price` may carry a `$` and thousands separators (`"$1,249.00"`). It is stored in
  whole cents. `0.00` is a valid price (promotional items).
- `qty` is a whole number of units. A blank `qty` means `0`.
- `updated_at` is `2026-04-01`, `04/01/2026` (month/day/year) or `2026-04-01T09:30:00`.
  A date without a time is midnight.
- `status` is `active` or `discontinued` (any case). Blank means `active`.

### Validation

Checks run in this order and the first failure is the row's reason:

1. `missing_sku`: the SKU is blank.
2. `unknown_category`: the category is not in the registry, or is inactive.
3. `bad_price`: the price is blank or not a number.
4. `bad_qty`: the quantity is not a whole number, or is negative.
5. `bad_date`: `updated_at` is not in one of the formats above (or is not a real date).

A row that fails is a reject `(source, line, reason)`. Every other row is accepted.

### Merge

- Accepted rows from all feeds are merged by SKU. The record with the latest
  `updated_at` wins. If two records have exactly the same `updated_at`, the one read
  later wins (a later feed, or a later line in the same feed).
- The winning record decides everything, including status: if the newest record for a
  SKU is `discontinued`, the SKU is discontinued even if an older record was active.
- The **catalog** is the winning records that are not discontinued.

### Report

`skufeed.reports.build_report()` returns:

- `accepted`: source → number of accepted rows.
- `rejects`: every reject as `(source, line, reason)`, in feed order then line order.
- `catalog`: SKU → `title`, `category`, `price_cents`, `qty`, `source` (of the winning
  record).
- `summary`:
  - `categories`: for each category in the **catalog**: `skus` (catalog SKUs),
    `units` (sum of `qty`), `avg_price` (mean price in dollars, rounded to 2 decimals)
    and `stock_value` (sum of price × qty in dollars, rounded to 2 decimals);
  - `top_category`: the category with the highest `stock_value` (ties: alphabetical);
  - `discontinued`: number of SKUs whose winning record is discontinued;
  - `duplicates_removed`: accepted rows minus distinct SKUs;
  - `rejected`: reason → number of rejects.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
