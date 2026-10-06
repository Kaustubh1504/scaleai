# set-078 interviewer notes

**Scenario:** An out-of-order event log is replayed through a labeling/review state machine with role checks, review-claim expiry, rework escalation and a final as_of sweep. Test 3 covers the review queue (paused projects excluded) and cycle times.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Claim treated as expired at its deadline

1. **Nudge:** Only T-10 has the wrong final state. Work out its claim deadline and compare it with as_of.
2. **Area:** Look at the expiry comparison used by the replay and the final sweep.
3. **Exact:** claim_expired should be `now > deadline`.

### B2: Duplicate key uses the raw actor id

1. **Nudge:** Look at the extra violation's line in events.csv and the line just above it.
2. **Area:** How does load_events decide that two rows are the same event?
3. **Exact:** Build the key from the normalised `actor`, not clean(row["actor"]).

### B3: `or` makes every decision count as approved

1. **Nudge:** rv-02 and rv-03 show approvals but no rejections. Check the log: did they ever approve?
2. **Area:** Look at how reviewer_decisions classifies each transition.
3. **Exact:** Write `t.action == "approve" or t.action == "resolve"` (or `t.action in (...)`).

### B4: Review samples stored on the class

1. **Nudge:** Every reviewer has the same mean. What would make their samples identical?
2. **Area:** Look at where ReviewTimer keeps its samples.
3. **Exact:** Create the list per instance: `self.samples = []` in __init__.

### B5: Removing paused tasks while iterating the queue

1. **Nudge:** T-07 is in a paused project but still in the queue, while T-06 (also paused) is gone. Where do they sit in the sorted list?
2. **Area:** Look at how build_queue drops paused tasks.
3. **Exact:** Iterate over a copy (`list(queue)`) or build a new filtered list.

### B6: Cycle time uses timedelta.seconds

1. **Nudge:** Only T-02 is off, by exactly 24 hours. What is special about it?
2. **Area:** Look at how cycle_hours turns the timedelta into a number.
3. **Exact:** Use .total_seconds() instead of .seconds.

## "Why did that fix work?" probes

**B1**
- T-10 now ends in submitted. Why doesn't it show up in the queue?
- Which other event in the log would also have changed if it had landed exactly on a deadline?

**B2**
- Why didn't the duplicate approve change T-01's state or rv-01's counts?
- If the duplicate had been a claim_review, would anything besides violations have changed?

**B3**
- Why were the claims counts still right?
- How would a linter or a quick REPL check catch this kind of expression?

**B4**
- Why does `self.samples.append(...)` change a class attribute, while `self.samples = [...]` wouldn't?
- Would building a fresh list in __init__ ever share state between timers?

**B5**
- Why was T-06 removed but not T-07?
- Would the problem show up if the two paused tasks weren't next to each other?

**B6**
- What does timedelta(days=1, hours=3).seconds return, and why?
- Why did review_minutes not have the same problem?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `revflow/machine.py` → `next_state`: Sending a reject back to LABELING instead of a 'rejected' state looks odd, but it is exactly the README table. The escalation compares the rework count *after* this reject with max_rework, so the second reject escalates when max_rework is 2.
- `revflow/backlog.py` → `priority_key`: -priority looks like a flipped sort, but the README says the higher number is more urgent, so negating it puts the most urgent first. Oldest created first and then task id match the spec.
