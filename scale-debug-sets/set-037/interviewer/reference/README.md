# Card Fraud Screen

A batch screen for one day of card transactions. Each transaction is converted to USD,
run through three rules (velocity, foreign use, daily limit), scored, and given an
action: allow, review or block. Rows that can't be read are set aside with a reason.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/transactions.csv`: `txn_id`, `card_id`, `amount`, `currency`, `country`, `timestamp`.
- `data/cards.json`: per card, `home_country` and `daily_limit_usd`.
- `data/rates.json`: `to_usd` multipliers per currency code.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Loading

- `txn_id`: trim, upper-case. `card_id`: trim, lower-case. `currency` and `country`: trim,
  upper-case. The same cleaning applies to ids and codes in `cards.json` and `rates.json`.
- `amount` may have a leading `$` and commas as thousands separators (`"1,050.00"`).
- `timestamp` is `2026-03-04 09:00:00`, `2026-03-04T09:00:00` or `03/04/2026 09:00`
  (month/day/year).
- A row is **rejected** instead of loaded when:
  - any of `txn_id`, `card_id`, `amount`, `currency`, `timestamp` is blank →
    reason `missing:<field>` (the first blank field in that order);
  - otherwise, `amount` or `timestamp` can't be parsed → reason `unparseable`.
- Rejected rows are reported in file order. Loaded transactions are scored in timestamp
  order.

### Rules (per card)

- **velocity**: the transaction is the 3rd (or later) on the card within a 10-minute
  window, counting itself. A transaction exactly 10 minutes after an earlier one is still
  inside that one's window.
- **foreign**: `country` is set and differs from the card's `home_country`.
- **over_limit**: after adding this transaction, the card's USD spend for that calendar
  day is above `daily_limit_usd`. Exactly at the limit is fine.

### Scoring

- USD amount = `amount × rate`, rounded to 2 decimals.
- Weights: velocity 40, foreign 30, over_limit 50. Score = sum of the flags' weights.
- Action: score ≥ 70 → `block`; ≥ 40 → `review`; otherwise `allow`. Flags are listed in
  the order velocity, foreign, over_limit.
- A transaction in a currency with no rate still gets a decision: `usd` is `None`, score
  40, flags `["unknown_currency:<CODE>"]`, action `review`. It does not count towards
  velocity or daily spend.

### Report

`fraudlens.reports.build_report()` returns:

- `decisions`: `{txn_id: {"card", "usd", "score", "flags", "action"}}` for every loaded
  transaction;
- `rejected`: `[{"txn_id", "reason"}]`;
- `summary`: `loaded`, `rejected` (counts), `total_usd` (sum of known USD amounts,
  rounded to 2 decimals) and `blocked` (sorted txn ids).

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
