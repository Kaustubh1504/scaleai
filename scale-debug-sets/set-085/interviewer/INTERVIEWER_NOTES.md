# set-085 interviewer notes

**Scenario:** Before a referral-bonus payout run, link accounts into rings by shared device or private IP, decide which referrals earn the $25 bonus (qualifying deposit, not a self-referral, once per referred account), flag self-referrals and signup bursts, and hold flagged referrers.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Device ids not case-folded

1. **Nudge:** Only one ring is affected and it loses exactly one member. What links acc-29 to the others?
2. **Area:** Look at how device ids are cleaned before build_rings groups by them.
3. **Exact:** clean_device trims but does not upper-case; the spec says trim and upper-case.

### B2: Burst gap uses the seconds field

1. **Nudge:** acc-03's referrals were days apart. Why would they count as a 60-minute burst?
2. **Area:** has_burst relies on a helper in timeutil.py to measure the gap.
3. **Exact:** `.seconds` drops the days; use `.total_seconds()`.

### B3: Bonus paid per deposit, not per account

1. **Nudge:** acc-04 has 2 qualifying referrals but is paid for 3. Which of its referred accounts deposited more than once?
2. **Area:** Look at how bonus_ledger avoids paying the same account twice.
3. **Exact:** `paid` is consulted but nothing is added to it; add `paid.add(acct.id)` before appending.

## "Why did that fix work?" probes

**B1**
- Why did acc-06 still get flagged for self-referral even before your fix?
- Why do the IP links not have the same problem?

**B2**
- Why were acc-04 (exactly 60 minutes) and acc-05 (61 minutes) unaffected?
- Why didn't the held list or releasable total change while this was present?

**B3**
- Why did qualifying stay at 2 for acc-04 while payout_usd went up?
- Why didn't releasable_usd catch this?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `refwatch/timeutil.py` → `within_days`: The spec makes the 14-day window inclusive at both ends (deposit at or after signup, exactly 14 days later still counts), which is exactly `timedelta(0) <= end - start <= timedelta(days=days)`. acc-25's deposit lands exactly 14 days after signup and must qualify; acc-26's lands 14 days and 1 hour later and must not. The `<=` looks like the classic boundary suspect but is correct.
- `refwatch/links.py` → `find`: Union-find with path halving: `parent[x] = parent[parent[x]]` points x at its grandparent before stepping, which only shortens paths and never changes which root a node reaches. It looks like it could skip or corrupt roots, but the root is the only node with parent[x] == x and the loop stops there.
