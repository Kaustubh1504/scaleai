# set-023 interviewer notes

**Scenario:** Price accepted tasks (flat or per-minute), halve late submissions, convert each contributor's earnings to their payout currency or hold them below a minimum, and list the top contributors by task count. Test 2 checks the payout report.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Elapsed hours drop whole days

1. **Nudge:** T106 and T121 were submitted days after assignment. Why are they paid in full?
2. **Area:** Look at how the elapsed time between two timestamps is computed.
3. **Exact:** hours_between uses .seconds; use .total_seconds().

### B2: Currency conversion truncates

1. **Nudge:** C04's payout is one rupee short. Multiply it out by hand.
2. **Area:** Look at how a USD amount becomes a local amount.
3. **Exact:** to_local uses int(); the spec says round to nearest: round(...).

### B3: Counter.update on an id string

1. **Nudge:** Look at the keys in top_contributors. Are they contributor ids?
2. **Area:** How are tasks counted per contributor?
3. **Exact:** counts.update(cid) counts characters; use counts[task.contributor_id] += 1 (or update([cid])).

## "Why did that fix work?" probes

**B1**
- Why was T113 (23 h 59 m) right with and without the fix?
- What does timedelta(days=3, hours=2).seconds return, and why?

**B2**
- Why is 1400 × 83.1 not exactly 116340 in Python?
- Rule 2 floors and rule 5 rounds. How do you tell which applies where?

**B3**
- What would counts.update([task.contributor_id]) do differently?
- Why didn't earned totals have the same problem?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `payroll/pricing.py` → `base_pay`: The `//` looks like an integer-division slip, but rule 2 says per-minute pay is rounded down to a whole cent, and multiplying before dividing keeps it exact.
