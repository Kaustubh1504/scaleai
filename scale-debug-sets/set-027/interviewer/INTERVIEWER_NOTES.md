# set-027 interviewer notes

**Scenario:** Replay lease/heartbeat/ack events (epoch-ms and ISO times mixed) against a priority queue where 1 is most urgent; report dispatch, heartbeat outcomes, per-worker completions and mean queue wait.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Heartbeat at the deadline accepted

1. **Nudge:** When was T02's deadline before the 08:01:50 heartbeat?
2. **Area:** Look at the comparison that decides a lease has run out.
3. **Exact:** reap uses `>`; README rule 1 says `now >= deadline`.

### B2: Completion list shared by every worker

1. **Nudge:** Every worker lists the same tasks. Where does each worker's list come from?
2. **Area:** Look at how Worker stores `completed`.
3. **Exact:** Assign `self.completed = []` in __init__ instead of at class level.

### B3: Mean wait reported in milliseconds

1. **Nudge:** The value is exactly 1000× the expected one.
2. **Area:** What unit are enqueued_ms and first_leased_ms in?
3. **Exact:** Divide the mean by 1000.

## "Why did that fix work?" probes

**B1**
- Why does T02 still get re-leased to w1 at 08:03:00 under both versions?
- What event would you add to the log to make this boundary visible in the dispatch log too?

**B2**
- Why does the list keep growing when the tests build the report more than once?
- Why would `self.completed = self.completed + [task_id]` have hidden the problem?

**B3**
- How would you rename things so this can't happen again?
- Which inputs are already in ms, and which get converted?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `leasebeat/broker.py` → `pick_next`: min() on (priority, enqueued_ms, task_id) looks like it might be backwards for priority, but this README says 1 is the most urgent, so the smallest number should win. The tie-breaks match rule 3.
- `leasebeat/loader.py` → `to_ms`: Treating an all-digit string as epoch milliseconds matches the README, and the parsed formats are pinned to UTC before converting, multiplying seconds by 1000.
