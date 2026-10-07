# Weekly Payout File

Contributors are paid once a week, per approved task, at a flat rate set for each project.
At the end of the week this tool prices the approved work, applies manual adjustments,
decides who is paid and who is held, and writes the payout file that is sent to the bank.
It also flags contributors who are working suspiciously fast so a reviewer can look at
them before the money goes out.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/period.json`: the pay period (`start`, `end`) and the `minimum_payout`.
- `data/contributors.csv`: the roster (`contributor_id`, `name`, `account_no`, `method`).
- `data/rates.csv`: one row per project (`project`, `rate_per_task`, `min_seconds`).
- `data/work_log.csv`: one row per submitted task. `duration_ms` is the time spent on the
  task in **milliseconds**.
- `data/adjustments.json`: manual bonuses (positive) and clawbacks (negative).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Ids are case-insensitive: trim and upper-case contributor and entry ids (`c-01 ` →
  `C-01`) wherever they appear, including the adjustments file.
- Project names: trim and lower-case. Work `status` and payout `method`: trim and
  lower-case.
- `account_no` is a whole number. It is written without leading zeros and may be of any
  length.
- Money values may carry a `$` and thousands separators (`$1,000.00`). A value in
  parentheses is negative (`(1.20)` → `-1.20`). All money is handled as exact decimals.
- `submitted_at` uses one of `2026-09-21 09:00`, `09/21/2026 09:00` (month/day/year) or
  `2026-09-21T09:00:00`.

### Payable work

1. A work entry is **payable** when all of these hold:
   - its status is `approved`;
   - its contributor is in the roster and its project is in `rates.csv`;
   - it was submitted inside the pay period. The period is half-open: the `start` date is
     included, the `end` date is **not** (an entry at 00:00 on the end date belongs to the
     next period).

### Statements

2. Every roster contributor gets a statement, even with no payable work.
3. `tasks` = number of payable entries; `gross` = sum of their project rates.
4. `adjustments` = sum of that contributor's adjustment amounts. Adjustments for ids not
   in the roster are ignored.
5. `net = gross + adjustments`. `gross`, `adjustments` and `net` are each rounded to whole
   cents, half up (`1.365` → `1.37`).
6. `status` is `paid` when `net` is at least `minimum_payout`, otherwise `held`.

### Audit flags

7. Flags are computed from **payable** entries only.
8. For each contributor and project, take the median `duration_ms` of their payable
   entries on that project, in seconds. If it is below the project's `min_seconds`
   (strictly), add the reason `fast:<project>`.
9. `flags` maps contributor id → list of reasons sorted by project. Contributors with no
   reasons are left out.

### Payout file and summary

10. `payout_file` has one line per **paid** contributor: `account_no,method,net`, sorted by
    account number in ascending numeric order.
11. `summary`: `paid` and `held` counts, and `totals_by_method`: method → total `net` of
    paid contributors (as a string with 2 decimals), sorted by method.

### Report

`paycalc.payfile.build_report()` returns `statements` (contributor id → `tasks`, `gross`,
`adjustments`, `net`, `status`; money as strings with 2 decimals), `flags`, `payout_file`
and `summary`.

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
