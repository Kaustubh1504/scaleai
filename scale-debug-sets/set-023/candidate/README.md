# Contributor Payouts

Contributors are paid for the labeling tasks they submit. Some task types pay a flat
amount per task and some pay by the minute. Each payout run converts a contributor's
earnings into the currency they are paid in, holds back balances below their minimum
payout, and lists the most active contributors.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/tasks.csv`: one row per task submission.
- `data/contributors.csv`: the contributor roster with payout currency and minimum payout.
- `data/rates.json`: pay rules per task type, the late-submission rule and the exchange
  rates (units of the payout currency per 1 USD).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- `task_id` and `contributor_id`: trim and upper-case (`c03` → `C03`).
- `task_type` and `status`: trim and lower-case. `currency`: trim and upper-case; blank
  means `USD`.
- A blank `min_payout_usd_cents` means `1000`. A blank `minutes` means `0`.
- Timestamps use one of `2026-05-04 09:00`, `05/04/2026 09:00` (month/day/year) or
  `2026-05-04T09:00`.
- Exchange rates may be numbers or numeric strings.

### Task pay (all amounts in USD cents)

1. Only tasks with status `accepted` from contributors in the roster are paid.
2. A `per_task_cents` task type pays that amount. An `hourly_cents` task type pays
   `hourly_cents × minutes ÷ 60`, rounded **down** to a whole cent.
3. A task is **late** when more than `late_after_hours` hours passed between
   `assigned_at` and `submitted_at` (count the full elapsed time, across days). A late
   task pays its amount × `late_factor`, rounded to the nearest cent.

### Payouts

4. A contributor's earnings are the sum of their task pay.
5. If earnings ≥ their minimum payout, they are paid: `payout` = earnings × the exchange
   rate for their currency, **rounded to the nearest** whole unit, and `held_usd_cents`
   is 0. Otherwise `payout` is 0 and the whole balance is held (`held_usd_cents` =
   earnings).

### Report

`payroll.reports.build_report()` returns:

- `task_pay`: task id → USD cents, for every paid task.
- `contributors`: for every roster contributor, `earned_usd_cents`, `currency`, `payout`
  and `held_usd_cents`.
- `top_contributors`: the three contributors with the most paid tasks, as
  `[contributor_id, count]` pairs, most tasks first (ties: lowest id).

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
