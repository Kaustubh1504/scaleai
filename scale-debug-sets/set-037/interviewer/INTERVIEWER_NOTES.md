# set-037 interviewer notes

**Scenario:** A one-day batch fraud screen: transactions are converted to USD, scored by velocity / foreign-use / daily-limit rules, and given allow/review/block actions; unreadable rows are rejected with a reason.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Velocity window drops the transaction exactly 10 minutes old

1. **Nudge:** How far apart are T002 and T006?
2. **Area:** Look at the eviction condition in velocity_hit.
3. **Exact:** Evict only entries strictly older than the window: use >.

### B2: Unknown-currency transactions silently skipped

1. **Nudge:** T011 was loaded (summary says 25 loaded). Where did its decision go?
2. **Area:** Follow what score_all does when evaluate raises.
3. **Exact:** In the except block, record a review Decision with the unknown_currency:<code> flag before continuing.

### B3: ValueError handler catches missing fields first

1. **Nudge:** T015 has no card_id. Why is its reason unparseable?
2. **Area:** Look at the class hierarchy of MissingFieldError and the order of the except clauses.
3. **Exact:** Put the MissingFieldError handler before the ValueError handler.

## "Why did that fix work?" probes

**B1**
- Why does c03's burst still get flagged with the change in place?
- What would happen if the deque were not reset per card?

**B2**
- Why isn't total_usd affected by this?
- If to_usd were called after velocity_hit in evaluate, what else would this exception path get wrong?

**B3**
- Why is the rejected count right even though the reasons were not?
- How else could you avoid this, without relying on clause order?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `fraudlens/money.py` → `parse_amount`: Stripping every comma looks like it could break decimal commas, but the README says commas are thousands separators. '1,050.00' -> 1050.0 and '12,000' -> 12000.0 are both right; '12.5O' still raises ValueError, which is what makes T024 unparseable.
