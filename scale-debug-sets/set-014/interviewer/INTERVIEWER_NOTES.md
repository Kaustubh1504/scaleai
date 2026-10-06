# set-014 interviewer notes

**Scenario:** Rebuild worker health (up/down/draining) from a probe log, replay requests through zone-affine weighted least-connections routing (ties: higher weight, then id), and report availability, assignments, peak concurrency and per-zone load.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Draining check compares an Enum to a string

1. **Nudge:** W-08 is configured as draining. Why does it end up down?
2. **Area:** Look at the check in apply_probes that is meant to skip draining workers.
3. **Exact:** Compare with the enum: `if worker.state is State.DRAINING:`.

### B2: Timeouts counted as passing probes

1. **Nudge:** W-04's only probe in the window is a timeout, yet its availability is 1.0.
2. **Area:** Compare how availability decides a probe passed with how apply_probes decides it.
3. **Exact:** Use `not is_failure(p)` instead of `p.result != "fail"`.

### B3: Weight dropped from the routing tie-break

1. **Nudge:** Every us-east worker is idle when R01 arrives. Which one does README rule 8 pick?
2. **Area:** Look at the sort key in router.pick_worker.
3. **Exact:** Add `-w.weight` between the load and the id: `(len(w.active) / w.weight, -w.weight, w.worker_id)`.

### B4: Starts counted before ends at the same instant

1. **Nudge:** Several requests end at exactly 10:00:03, when new ones start. Should they overlap?
2. **Area:** Look at how peak_in_flight orders events that share a timestamp.
3. **Exact:** Sort by (time, delta) so -1 comes before +1: `key=lambda e: (e[0], e[1])`.

### B5: served list shared by every worker

1. **Nudge:** Each zone reports a multiple of 19, the total number of routed requests. Why?
2. **Area:** Look at where Worker.served is created.
3. **Exact:** Create the list per instance in __init__: `self.served = []`.

### B6: Mean duration uses floor division

1. **Nudge:** ap-south shows 1316 but the durations average 1316.67. Where is the fraction lost?
2. **Area:** Look at the mean in reports.zone_summary.
3. **Exact:** Use true division `/` instead of `//`.

## "Why did that fix work?" probes

**B1**
- Why didn't routing change, even though W-08's state was different?
- What would make `State.DRAINING == "draining"` true, and why might you not want that?

**B2**
- Why did W-04's state stay up even though its last probe failed?
- W-05 has two passing probes but availability None. Why is that correct?

**B3**
- Why did the per-zone totals and peak stay the same even though many assignments moved?
- Why is the weight negated instead of using max()?

**B4**
- Why did routing itself handle the same boundary correctly?
- Would a plain events.sort() give the right answer here? Why?

**B5**
- Why does `active` not have the same problem, even though it is also a list?
- Why did the mean durations stay right while served was inflated?

**B6**
- Why did eu-west come out right with this bug?
- Why doesn't round(..., 1) bring the decimal back?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `lbsim/router.py` → `release_finished`: `end > now` keeps only connections that are still open. A connection that ends exactly when a request arrives is closed for that request, as README rule 6 says, so `>` (not `>=`) is right.
- `lbsim/loader.py` → `parse_time`: It covers exactly the three timestamp formats the README lists, with month/day order for the slash format.
