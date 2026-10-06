# Contributor Roster Ingestion

Three vendors send contributor exports in different shapes: two CSV files (one of them
saved by a spreadsheet tool) and a JSON dump. This tool validates every row, drops
inactive contributors, merges people who appear more than once (in one file or across
files), and exports a single roster as JSON.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/sources.json`: source name → `file` and `priority`. **Priority 1 is the most
  trusted source**; larger numbers are less trusted.
- `data/vendor_a.csv`, `data/vendor_b.csv`: CSV exports. Column order differs between
  files, and a file may start with a UTF-8 byte-order mark.
- `data/vendor_c.json`: a list of objects with the same fields. `skills` may be a list or
  a `;`-separated string.

Fields: `email`, `name`, `country`, `skills`, `hours_per_week`, `updated_at`, `active`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Source names: trim and lower-case. Sources are processed in sorted name order.
- `email`: trim, lower-case, drop a leading `mailto:`. Names: collapse runs of spaces.
  Country: trim and upper-case.
- `skills`: split strings on `;`, trim and lower-case each skill, and **drop empty
  entries** (`"python;"` → `["python"]`, a blank cell → `[]`).
- `updated_at`: `2026-03-01 09:30`, `03/01/2026 09:30` (month/day/year),
  `2026-03-01T09:30:00`, or a bare date `2026-03-01` (meaning midnight).
- `active`: a JSON boolean, or a string where `true`, `yes`, `y`, `1` (any case) mean
  active and anything else means inactive. Missing, blank or `null` means active.

### Validation (first failing rule wins)

1. Blank email → rejected, `missing email`.
2. No `@`, an empty part before it, or no `.` in the domain → `invalid email`.
3. `updated_at` in none of the formats above → `unparseable date`.
4. `hours_per_week` not a number, or outside 0–60 inclusive → `invalid hours`.
5. Inactive → not rejected, but counted as `inactive` and left out of the roster.

Rows are numbered from 1 (the first data row) within each source.

### Merging

All accepted rows that share an email are one contributor:

- the **winning row** is the one with the latest `updated_at`; on an exact tie, the row
  from the most trusted source wins. `name`, `country`, `hours` and `updated_at` come from
  the winning row;
- `skills` is the sorted set of every skill across all of that person's rows (no
  repeats); `sources` is the sorted list of distinct sources they appeared in;
- `duplicates` is the number of emails that had more than one accepted row.

### Report

`rosterflow.reports.build_report()` returns:

- `sources`: per source `rows`, `accepted`, `rejected`, `inactive`;
- `rejected`: `{"source", "row", "reason"}` in source order, then row order;
- `roster`: email → `name`, `country`, `hours`, `skills`, `sources`;
- `duplicates`;
- `skill_counts`: skill → number of roster contributors with that skill;
- `countries`: country → number of roster contributors;
- `export`: the roster as a JSON string: a list sorted by email, each object with
  `email`, `name`, `country`, `hours`, `skills`, `sources` and `updated_at` as an
  ISO-8601 string (`2026-03-01T09:30:00`).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the exported roster
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
