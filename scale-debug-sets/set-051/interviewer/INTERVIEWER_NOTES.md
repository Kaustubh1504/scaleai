# set-051 interviewer notes

**Scenario:** Replay a day of claim/heartbeat/ack events against per-queue tasks with ten-minute leases that heartbeats can extend twice. Test 2 summarises workers, dead letters and extensions.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Event task ids only trimmed, not upper-cased

1. **Nudge:** Look at the rejected list: dan's ack of T04 at 09:31 is rejected, yet dan claimed T04 at 09:22. Look at how that row is written in events.csv.
2. **Area:** Compare how task ids are normalised in load_tasks and in load_events.
3. **Exact:** load_events uses clean(row["task"]); it needs norm_task(row["task"]).

### B2: Reap removes leases from the list it is looping over

1. **Nudge:** cara's 09:12 ack of T04 should be rejected: her lease ended at 09:11. Why does the ledger still think she holds it?
2. **Area:** Look at what happens in reap() when two leases expire at the same moment.
3. **Exact:** reap() removes from self.active while looping over it; loop over list(self.active) instead.

### B3: Third heartbeat accepted

1. **Nudge:** alice sent three heartbeats for T01. How many should have been accepted?
2. **Area:** Look at the extension limit check in heartbeat().
3. **Exact:** `lease.extensions > MAX_EXTENSIONS` should be `>=`.

## "Why did that fix work?" probes

**B1**
- Why were every one of the heartbeats rejected, but only some of the acks?
- Why did fixing this change which task bob's 10:20 claim received?

**B2**
- Why does it matter that bob's and cara's leases are next to each other in self.active?
- Would the skipped lease ever be reaped? When, and why is that still too late?

**B3**
- Why couldn't you see this while event task ids weren't upper-cased?
- The comment says 'up to MAX_EXTENSIONS times'. What test would pin the boundary down?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `leasebook/ledger.py` → `next_pending`: It uses min() on (priority, created_at, id). That looks backwards to anyone who reads 'priority' as 'bigger wins', but the README says 1 is the most urgent, so the smallest number has to come first.
