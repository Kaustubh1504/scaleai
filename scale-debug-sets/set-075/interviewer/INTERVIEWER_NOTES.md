# set-075 interviewer notes

**Scenario:** Replay a millisecond event log (poll/heartbeat/ack/fail) through a lease broker with boundary-inclusive expiry, then report final task states, a checkpoint snapshot, rejection codes and hand-out wait times.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Checkpoint snapshot is a shallow copy

1. **Nudge:** The checkpoint view is identical to the final view. Was it ever different?
2. **Area:** Look at what snapshot() actually copies.
3. **Exact:** Copy the Task objects too: copy.deepcopy(tasks).

### B2: Base exception matched first

1. **Nudge:** Every rejection is 'invalid', but only one event names a task that does not exist.
2. **Area:** How does rejection_code pick a code, and how are the exception classes related?
3. **Exact:** Put the subclasses before LeaseError in REJECTION_CODES.

### B3: max wait reported in milliseconds

1. **Nudge:** mean_s looks right but max_s is 1000 times too big.
2. **Area:** Compare how the two wait figures are converted.
3. **Exact:** Divide max(waits) by 1000 as well.

## "Why did that fix work?" probes

**B1**
- Why does a new dict not protect the snapshot?
- Would copy.copy(tasks) have been enough? Why not?

**B2**
- Where else in Python does handler order matter in the same way?
- The comment says 'most specific first'. What should that have told you?

**B3**
- Which task has the 230 s wait, and why is it so long?
- Why is T06's wait 0 even though it was enqueued after the replay started?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `leasebox/broker.py` → `lease_expired`: `>=` looks like it expires leases one tick early, but rule 2 says a lease expiring at or before the event time has expired. W3's heartbeat at exactly 70 s on a lease expiring at 70 s must be rejected.
- `leasebox/broker.py` → `next_task`: min() over (priority, enqueued_ms, id) looks like it might pick the least important task, but priority 1 is the most urgent, so the smallest tuple is the right one. It also filters out tasks enqueued after now (T06 before 60 s).
