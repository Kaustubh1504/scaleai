# Vendor Roster Ingestion

Three labelling vendors send us roster exports of the contributors they manage. The same
person often appears in more than one export, with slightly different details. This tool
reads every export, validates and cleans each row, merges duplicates into one record per
contributor, and reports what was loaded and what was rejected.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

Every `.csv` and `.json` file in `data/` is one vendor export; the vendor name is the file
name without its extension (`vendor_a`). Exports are read in file-name order. Each row
has `source_ref`, `email`, `name`, `skills`, `hourly_rate`, `country` and `updated_at`,
but column order and header case differ between vendors, and some exports are saved with
a UTF-8 byte-order mark.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Reading

1. Column names are matched after trimming and lower-casing. A byte-order mark at the
   start of a file is not part of the first column name.
2. `row` numbers count data rows from 1 within each file (the header is not a row).

### Validating a row

3. A row with a blank or absent `email` is rejected with reason `missing_field`.
4. A row is rejected with reason `invalid_value` when the email (trimmed, lower-cased)
   does not have exactly one `@`, has a space, or has no `.` after the `@`; when
   `updated_at` is not one of `2026-04-01`, `04/01/2026` (month/day/year) or
   `2026-04-01T09:30:00`; or when `hourly_rate` is present but not a number, or negative.
5. When a row has several problems, the reason for the first problem in the order above
   wins (`missing_field` before `invalid_value`).

### Cleaning a row

6. `name`: trimmed. If blank, use the part of the email before `@` and add the note
   `name_from_email`.
7. `skills`: split on `;`, trim, lower-case, drop blanks, unique, sorted.
8. `hourly_rate`: an optional leading `$` is ignored. A value ending in `/day` is a day
   rate for an 8-hour day, so it is divided by 8. Round to 2 decimals. `0` is a valid
   rate. A blank or absent rate is `None` and adds the note `rate_missing`.
9. `country`: trim and upper-case, then map `USA`/`UNITED STATES` → `US`, `UK` → `GB`,
   `INDIA` → `IN`. A blank country is `UNKNOWN`.
10. `sources`: `"<vendor>:<source_ref>"`.
11. Each row's `notes` start empty and only collect the notes from that row.

### Merging duplicates

12. Accepted rows with the same email are one contributor.
13. The row with the latest `updated_at` wins and provides `name`, `vendor`,
    `hourly_rate`, `country` and `notes`. On equal `updated_at` the row read later wins.
14. `skills` is the sorted union of all the rows' skills, without repeats, and `sources`
    is the sorted list of all the rows' sources.

### Report

`rosterload.report.build_report()` returns:

- `records`: per email, `name`, `vendor`, `skills`, `hourly_rate`, `country`, `notes`,
  `sources`;
- `rejected`: `{file, row, reason}` for every rejected row, in reading order;
- `summary`: `accepted_by_vendor` (records per winning vendor), `duplicates_merged` (the
  number of accepted rows absorbed into another row), `rejected_by_reason` and
  `countries` (records per country).

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
