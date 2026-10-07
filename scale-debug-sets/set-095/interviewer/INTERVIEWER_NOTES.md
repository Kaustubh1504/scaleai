# set-095 interviewer notes

**Scenario:** Price approved tasks at flat per-project rates inside a half-open week, add manual adjustments, mark contributors paid or held against a minimum, flag contributors whose median task time is below a project floor, and write a bank payout file sorted by account number. Test 2 checks the report.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Adjustment ids are not upper-cased

1. **Nudge:** Only C-01's adjustment is missing. How is its row written in adjustments.json?
2. **Area:** Compare how ids are cleaned in load_contributors and load_work with load_adjustments.
3. **Exact:** load_adjustments trims the id but does not call .upper().

### B2: Audit runs over every work entry

1. **Nudge:** C-11 is not on the roster and w09 was rejected. Why do they show up in the flags?
2. **Area:** audit.py only groups what it is given. Look at what build_report passes in.
3. **Exact:** build_report calls audit_flags(work, ...); spec rule 7 wants the payable entries.

### B3: Account numbers kept as text

1. **Nudge:** The lines are all there; only the order is off. What order are they in?
2. **Area:** payout_lines sorts by account_no. What type is it when it gets there?
3. **Exact:** load_contributors must convert account_no with int().

## "Why did that fix work?" probes

**B1**
- Why was C-03's adjustment (`"C-03 "`) fine before the fix?
- C-01 stays held with or without the fix. Why did no other test notice?

**B2**
- Why didn't w14 (end-date midnight) or w18 (pending) change any flag even when they were included?
- Where would you have to look if audit.py had been the cause instead?

**B3**
- Why does the printed payout line look the same whether account_no is a str or an int?
- Would sorting with key=lambda c: int(c.account_no) in payfile.py also have worked? Which fix is better and why?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `paycalc/loader.py` → `parse_amount`: The parenthesised-negative branch looks like it could drop the sign or choke on `$`/`,`, but it strips `$` and `,` first and returns -Decimal for `(1.20)`, exactly as the spec says. It is the obvious suspect for C-01's missing clawback, but the value is parsed fine; the id never matches.
- `paycalc/earnings.py` → `in_period`: Comparing a date with `< period.end` looks like it drops the last day, but the spec makes the period half-open: w14 at 2026-09-28 00:00 belongs to the next week and w05 at 09-27 23:59 counts.
