# Weekly Payout Run

Contributors are paid every week for the annotation work they complete. Operations exports
the contributor roster, the work log and a sheet of manual adjustments (bonuses and
clawbacks), and this tool turns them into payout statements. Amounts are whole US cents
throughout.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/contributors.csv`: the roster (`contributor_id`, `name`, `tier`, `carryover_cents`, `active`).
- `data/work_log.csv`: one row per completed work entry.
- `data/adjustments.csv`: manual bonuses and clawbacks, entered in **dollars**.
- `data/rates.json`: pay period, per-unit rates (cents), tier percentages, payout minimum.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- All CSV files are UTF-8. Some are saved from spreadsheet tools and begin with a
  byte-order mark; the header must still be read normally.
- Header names and cells may have stray spaces. Ids (`contributor_id`, `entry_id`) are
  case-insensitive: trim and upper-case them (`c02 ` → `C02`).
- `tier`, `task_type`, `status` and adjustment `kind` compare case-insensitively.
- `active` is true for `y`, `yes`, `true` or `1` (any case); anything else is false.
- A blank `carryover_cents` means `0`. Carryover may be negative (money owed back).
- `completed_at` uses one of `2026-09-28 09:15`, `09/29/2026 14:00` (month/day/year)
  or `30 Sep 2026 16:45`.
- Adjustment `amount` is in dollars and may have a leading `$` (`$5` → 500 cents).
- If an `entry_id` appears more than once in the work log, only its **last** row counts.

### Earnings

1. Only **active** contributors get a statement.
2. A work entry counts when all of these hold:
   - its status is `approved` or `auto-approved`;
   - its `task_type` has a rate in `rates.json` (other task types are not paid);
   - `completed_at` falls inside the pay period. Both the start and the end **dates**
     are included in full (an entry at 23:59 on the end date counts).
3. An entry's amount = `units × cents_per_unit`, then scaled by the contributor's tier
   percentage (gold 120 %, silver 110 %, standard 100 %). Round **half up** to a whole
   cent, per entry.
4. `earned` is the sum of the counted entries; `lines` is how many entries counted.

### Adjustments

5. Each adjustment row is a `bonus` or a `clawback` for one contributor. `bonus` and
   `clawback` on a statement are the totals of **that contributor's** rows (both
   positive numbers). Rows with any other kind are ignored.
6. Adjustments whose contributor is not in the roster are **unmatched** and counted in
   the summary. Adjustments for inactive contributors are simply not paid.

### Settlement

7. `gross = earned + bonus − clawback + carryover`.
8. If `gross` is at least `min_payout_cents`, the whole gross is paid and
   `carry_forward` is 0. Otherwise nothing is paid and the gross is carried forward.

### Report

`payrun.reports.build_report()` returns:

- `statements`: contributor id → `lines`, `earned`, `bonus`, `clawback`, `gross`,
  `paid`, `carry_forward`.
- `summary`: `total_paid`, `paid_contributors` (sorted ids with `paid > 0`), `held`
  (sorted ids with nothing paid) and `unmatched_adjustments`.

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
