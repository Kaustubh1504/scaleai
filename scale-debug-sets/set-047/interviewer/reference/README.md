# Contributor Pay Cycle

Contributors are paid per approved task, plus any one-off bonuses. At the end of each
pay period this tool works out every contributor's statement: task earnings, bonuses,
the platform fee, and whether the net amount is large enough to pay out now or has to
carry over to the next period.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/period.json`: `start`, `end`, `fee_percent`, `min_payout`.
- `data/rates.csv`: pay per task, by `task_type`.
- `data/tasks.csv`: one row per completed task (`task_id`, `contributor_id`,
  `task_type`, `status`, `completed_at`).
- `data/bonuses.csv`: one row per bonus (`contributor_id`, `amount`, `reason`), exported
  from the finance spreadsheet.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Contributor and task ids: trim and upper-case (`c-04 ` → `C-04`). Task types and
  statuses: trim and lower-case. CSV header names: trim and lower-case.
- Money is written as `12.50`, `5`, `$25` or `$1,000.00`. All amounts are handled in
  whole cents, rounding half-cents up.
- Timestamps use `2026-04-02 09:15`, `04/02/2026 09:15` (month/day/year),
  `2026-04-02T09:15:00`, or a bare date `2026-04-02` (midnight).
- A CSV file may start with a byte order mark; it is not part of the first header name.

### Task earnings

1. A task pays its `rate` only if its status is `approved` and its type is in
   `rates.csv`.
2. The period is **half-open**: a task counts when `start <= completed_at < end`. A task
   completed exactly at `end` belongs to the next period.
3. A task id that appears more than once is paid once (the first row counts).

### Bonuses

4. Every bonus row with a contributor id and an amount counts. Rows with a blank amount
   are skipped. Bonuses are not limited to the period dates.

### Statement

5. `gross` = task earnings + bonuses.
6. `fee` = `gross` × `fee_percent` / 100, rounded to the nearest cent with halves rounded
   **up** (26.5 cents → 27).
7. `net` = `gross` − `fee`. A contributor is `paid` when `net` is at least `min_payout`;
   otherwise `carried_over`.

`paycycle.statement.build_statement()` returns:

- `lines`: one entry per contributor with task earnings or a bonus, sorted by id, with
  `base_cents`, `bonus_cents`, `gross_cents`, `fee_cents`, `net_cents`, `status`;
- `paid` and `carried_over`: contributor ids in id order;
- `total_paid_cents`: the sum of `net_cents` over paid contributors.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the statement
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
