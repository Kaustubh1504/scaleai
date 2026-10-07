# Referral Payout Review

A savings app pays a referrer **$25** for each friend who signs up with their link and
makes a qualifying first deposit. The bonus attracts abuse: people "refer" accounts they
control themselves (same phone, same home network), or sign up a batch of accounts in a
few minutes. Before each payout run, this tool links accounts into rings, works out which
referrals earn a bonus, flags suspicious referrers, and produces the review report the
payments team signs off on.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/accounts.csv`: one row per account: `account_id`, `referred_by` (blank for
  organic signups), `signup_at`, `device_id` (blank when unknown).
- `data/deposits.csv`: `deposit_id`, `account_id`, `amount`, `status`, `deposited_at`.
- `data/logins.json`: `shared_networks` (public IPs such as office or café Wi-Fi) and
  `logins`, a list of `{account, ip, at}`. Login times are not used.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Account ids, wherever they appear (`account_id`, `referred_by`, deposit `account_id`,
  login `account`): trim and lower-case (` ACC-02` → `acc-02`).
- Device ids: trim and upper-case (` dv-60` → `DV-60`). A blank device id means no device.
- IPs (in `logins` and `shared_networks`): trim.
- Timestamps are `2026-06-01 09:00`, `2026-06-01T09:00:00` or `06/01/2026 09:00`
  (month/day/year).
- `amount` may have a leading `$` and thousands commas (`"$1,200.00"`). Deposits with a
  blank amount are ignored. `status` is compared after trimming, ignoring case.
- A `referred_by` that is not a known account is treated as blank (organic signup).
  Deposits and logins for unknown accounts are ignored.

### Rings

1. Two accounts are **linked** when they have the same device id, or when both have a
   login from the same IP and that IP is not in `shared_networks`.
2. Links are transitive: a **ring** is a group of 2 or more accounts connected by links.
   Accounts without links are not in any ring.
3. Rings are listed with ids sorted inside each ring, largest ring first, ties by the
   first id.

### Referrals

4. A referred account **qualifies** when it has at least one deposit that is `settled`,
   at least `20.00`, and made at or after its signup and no more than 14 days after it
   (exactly 14 days later still counts).
5. A referral is a **self-referral** when the referred account and its referrer are in the
   same ring, whether or not it qualifies. Self-referrals never earn a bonus.
6. Every other qualifying referred account earns its referrer one $25 bonus, **once per
   referred account**, no matter how many qualifying deposits it makes.
7. A referrer has a **burst** when 3 or more of the accounts it referred (qualifying or
   not) signed up within 60 minutes of each other: first to last of the three is at most
   60 minutes (exactly 60 counts).

### Report

`refwatch.report.build_report()` returns:

- `rings`: as in rule 3.
- `referrers`: for every account that referred at least one known account, sorted by id:
  `referred`, `qualifying`, `self_referrals`, `payout_usd` (total bonus earned under rule 6),
  `flags` (`self_referral` if it has any self-referral, then `burst`) and `held`
  (true when it has any flag).
- `summary`:
  - `held`: sorted ids of held referrers;
  - `releasable_usd`: total `payout_usd` of referrers that are **not** held;
  - `top_referrer`: the not-held referrer with the highest `payout_usd`; ties go to the
    lowest id (`null` if every referrer is held).

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
