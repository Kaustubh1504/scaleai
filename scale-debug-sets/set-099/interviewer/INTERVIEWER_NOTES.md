# set-099 interviewer notes

**Scenario:** Replay claim/heartbeat/ack/nack events against a lease broker with per-type lease lengths (priority 1 = most urgent). Every event reaps expired leases first. Rejections are classified through an exception hierarchy, and the report ends with mean first-claim-to-ack seconds per type.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Leases removed while iterating

1. **Nudge:** Two leases ran out before the 08:02:30 event. How many expiries are logged at 08:02:30?
2. **Area:** Look at how reap walks the lease list while it removes expired ones.
3. **Exact:** Iterate over a copy: `for lease in list(self.leases):`.

### B2: Generic lease error matched before TaskClosed

1. **Nudge:** K02 was already done at 08:04. Which reason should that ack get?
2. **Area:** Look at how a raised exception is turned into a reason string.
3. **Exact:** In REJECTION_REASONS, put (TaskClosed, "closed") above (LeaseError, "not_holder").

### B3: Mean ack time floor-divided

1. **Nudge:** Only some of the means are off, and those lose their decimals. Why would review be fine?
2. **Area:** Look at how ack_times turns the spans into a mean.
3. **Exact:** Use true division: `round(sum(s) / len(s), 1)`.

## "Why did that fix work?" probes

**B1**
- Why did nothing else in the report change, given that K05 stayed 'leased' for one extra event?
- Describe event data that would have turned this into a wrong final status.

**B2**
- Why were unknown_task and unknown_worker still reported correctly?
- How would the same mistake look written as try/except clauses?

**B3**
- Why is the int() around total_seconds() harmless here?
- Which value in the data made review come out right anyway?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `leasehold/broker.py` → `is_expired`: `>=` looks like an off-by-one, but rule 1 says a lease is expired when now >= expires_at, so a lease ending exactly at an event's time is reaped before that event.
- `leasehold/broker.py` → `pick_next`: min() over (priority, created_at, id) looks like it might pick the least urgent task, but priority 1 is the most urgent here, so the smallest number first is right. Earliest creation and lowest id are the tie-breaks from rule 3.
