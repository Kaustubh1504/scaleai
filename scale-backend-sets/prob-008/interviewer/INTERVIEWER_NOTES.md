# prob-008 — Annotator Earnings Calculator (interviewer notes)

**Kind:** api-client. The candidate inherits an intern's payout script and must
make it query the platform API correctly: four collections with three
pagination styles and three envelopes, joined (submissions → tasks for the
reward, → reviews for the verdict, → annotators for status), over messy JSON,
then publish payouts without ever paying twice.
**Difficulty:** medium · **Mode:** plain Python (library + CLI) · **Starter:** repo · **Planted bugs:** none
(the starter has *existing defects* the candidate must find by reading; see below)

## Setup

```bash
python tools/export_candidate.py prob-008 ~/interview --part1-only
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-008 python -m pytest prob-008/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-008/interviewer/hidden_tests -m "not change"   # gold bonus not delivered
```

Hidden tests build the API from `shared/` with **seed 83**, other sizes and other
credentials, and compute expected reports with an oracle over `api.canonical(...)`
(clean values), while the wire is messy. They call
`EarningsClient(http, client_id, client_secret, clock)`,
`compute_earnings(client, period_start, period_end)` and
`publish_payouts(client, report)`.

## What the candidate should learn from reading the repo (first ~5 minutes)

`earnings/client.py` has working auth and a `list_all()` that reads **only the
first page** and assumes a `data` envelope (only true for cursor collections).
`earnings/calc.py`:

* `in_period` uses `<=` on both ends (end must be exclusive);
* pays for **every** submission, ignoring reviews entirely;
* money is float dollars (`/ 100`, `round`, then `int(usd * 100)` truncates: 0.29 → 28);
* `int(task["reward_cents"])` crashes on `null` and silently accepts nothing else;
* `parse_ts` only handles ISO strings.

`tests/test_earnings.py` encodes the old behaviour (e.g. `earnings_usd`), so the
candidate must decide to change tests, not just code. A strong candidate lists
these defects before writing anything; a weak one discovers them one failing
test at a time.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–6 | Hand over `PART1.md`. Candidate reads `API.md` (pagination table), the starter, `data/recorded/`. |
| 6–16 | Pagination per collection, latest-review verdict, half-open period, integer cents. |
| ~14 | **Drop the mid-part change** (below), once a full-data report comes out. |
| 16–22 | Gold bonus, tests with `api.insert`. Reveal `PART2.md`. |
| 22–38 | Part 2: normalization layer (timestamps incl. epoch ms, digit-string rewards, unknown rewards, booleans, casing), on-hold rows, `payable_cents`. |
| 38–55 | Part 3: retry policy on every request, `publish_payouts` with idempotency keys, failure isolation, CLI `--publish`. |
| 55–60 | Follow-up discussion. |

If behind at minute 25, reveal Part 2 anyway. If behind at minute 45, skip
retries and implement `publish_payouts` with idempotency keys only.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–4 | `PART1.md`, read the starter and `API.md`. |
| 4–20 | Pagination for all four collections, verdict rule, cents. Skip the change unless done by minute 16. |
| 20–22 | Reveal `PART2.md`. |
| 22–28 | Timestamp normalization (the epoch-ms threshold) and unknown rewards. |
| 28–30 | Follow-up #1. |

Run `test_part1.py -m "not change"` and `test_part2.py`; score Part 3 categories "not observed".

## Mid-part requirement change (Part 1, ~minute 14)

Say, verbatim:

> "Finance wants to reward accuracy on gold tasks. An approved submission on a
> task with `is_gold` true earns a bonus of 50% of the task's reward, rounded
> down to whole cents, when its `answer.label` equals the task's `gold_label`
> (compare trimmed, case-insensitive). Include the bonus in `earnings_cents` and
> also report it per row as `gold_bonus_cents`. No bonus when the reward is unknown."

Additive: base tests ignore `gold_bonus_cents` and compute expected earnings
the same way the candidate does, with or without the bonus (they detect whether
rows carry the key). It tests whether the per-submission earning is one function
the candidate can extend, and whether they reach for `//` (integer cents) rather than floats.
Hidden tests: `test_part1.py::test_gold_bonus_*` (`change`).

## Planted bugs

None (beyond the starter's documented defects above, which are the point of Part 1).

## Hint ladder

**Part 1**
1. "How many records does `/v1/tasks` have, and how many does `list_all` return?"
2. "Open `API.md`'s pagination table: what changes per collection?" (params, envelope key, stop condition)
3. "Write the verdict lookup as its own function over all reviews: submission_id → latest verdict."

**Part 2**
1. "Run against `make_api()` and print `api.rendered('submissions')[:5]`. What forms do the timestamps take?"
2. "How do you tell epoch seconds from milliseconds?" (the `>= 10**11` rule in PART2)
3. "Normalize at the boundary: one module that turns wire values into canonical ones, used everywhere."

**Part 3**
1. "If the POST succeeded but you never saw the response, what happens on retry?" (idempotency key → replay, 200)
2. "Should one annotator's failure stop the run?" (no; record and continue; but auth errors stop)
3. "Put retries in the one place every request goes through."

## Common pitfalls (what the hidden tests catch)

* Only the first page of some collection, or the wrong envelope key (`data` vs `items` vs `results`).
* Offset pagination stopping on a short page instead of `total`.
* End-inclusive period; comparing naive and aware datetimes; treating naive ISO as local time.
* Earliest review instead of latest; tie on `created_at` not broken by highest id; reviews filtered by period.
* Float dollars anywhere (`0.1 + 0.2` errors show up in totals).
* `int("12")` fine but `None` → crash, or `None` silently treated as 0 earnings without listing the task.
* Epoch milliseconds parsed as seconds (dates in the year 56000).
* On-hold annotators dropped from rows instead of shown with `on_hold: true`.
* Publishing on-hold or zero rows; no `Idempotency-Key`, or a key that includes the amount or a timestamp.
* A transient failure on one payout aborting all later payouts; or swallowing `AuthError`.

## Follow-up questions

**1. "Why integer cents, and where is rounding allowed?"**
Strong: floats can't represent most decimal fractions; sums drift; store and
compute in the smallest unit; round once, at a defined point, with a defined rule
(here floor for the bonus, which favours the company; say so to finance); reconcile
totals between report, sink and ledger and alert on any difference.

**2. "Next month the same period is re-run and an annotator's amount changed because a review was overturned. What happens with your idempotency key?"**
Strong: the key makes the second POST a replay of the *old* amount, so the
correction is silently lost; idempotency keys guarantee one effect per key, not
correctness. Options: key on (period, annotator, version) and post adjustments as
separate ledger entries (credit/debit), never mutate a paid amount; compare the
replayed body with what you meant to send and flag mismatches.

**3. "How would you notice that the API started sending a new date format?"**
Strong: the normalizer raises on unknown forms (it must never guess), so the job
fails loudly; plus data-quality metrics per run (count of unknown rewards, records
per wire variant, rows on hold) with alerting on jumps; contract tests on recorded
samples; a quarantine path so one bad record doesn't block everyone else's pay.

## Reference solution

`reference/earnings/`: `client.py` (one `_send` with the retry policy, a
`COLLECTIONS` table driving all three pagination styles, `post()` with
`Idempotency-Key`), `normalize.py` (one function per wire rule, `DataError` on
anything unknown), `calc.py` (pure `latest_verdicts` and `summarize` over records,
gold bonus as one helper), `payouts.py` (`publish_payouts` with per-annotator
isolation), `cli.py` (atomic CSV write, `--publish`).

Lines a candidate must add: Part 1 ≈ 85 (incl. gold bonus ≈ 8), Part 2 ≈ 60, Part 3 ≈ 75.
