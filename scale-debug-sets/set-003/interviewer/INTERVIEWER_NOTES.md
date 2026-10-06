# set-003 interviewer notes

**Scenario:** Replay a lease/complete event log against a priority queue (higher number = more urgent). Leases last 15 minutes. Expired tasks go back to pending, or to dead once they have used max_attempts.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Priority loaded as a string

1. **Nudge:** Which task did the very first lease get, and what's its priority compared with A-101's?
2. **Area:** pick_next is verified, so check what type of value it is sorting.
3. **Exact:** load_tasks keeps priority as a str. Wrap it: int(clean(row["priority"])).

### B2: Lease age measured with timedelta.seconds

1. **Nudge:** Look at A-110's lease: when was it taken, and when did w4 complete it?
2. **Area:** Look at how reap measures the age of a lease.
3. **Exact:** Use (now - lease.leased_at).total_seconds(), not .seconds.

### B3: Dead-letter check allows one extra attempt

1. **Nudge:** How many times was A-110 leased, and what is its max_attempts?
2. **Area:** Look at the condition that decides dead versus pending.
3. **Exact:** Task.exhausted uses >; it should be attempts >= max_attempts.

## "Why did that fix work?" probes

**B1**
- Why would '-t.priority' in a one-pass sort have crashed right away, while this version silently gave the wrong order?
- Show a pair of priorities that compares the same way as strings and as ints, and a pair that doesn't.

**B2**
- Why did every same-day expiry still work?
- What would .seconds give for a negative timedelta, say if events were out of order?

**B3**
- Why couldn't you see this until the lease-age fix?
- A-103 has max_attempts 1. Why does it never reach the dead-letter check at all?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `leasequeue/broker.py` → `pick_next`: It is a two-pass stable sort. The first pass orders by (created_at, id) and the second by priority, descending. Python's sort is stable, so ties on priority keep the created_at/id order. It looks backwards, but it is correct, as long as priority is really an int.
