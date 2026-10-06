# set-062 interviewer notes

**Scenario:** Replay ten seconds of traffic against a worker pool with health transitions. Requests stay in their zone and go to the lowest running/effective-weight worker (degraded halves the weight). Report assignments, per-worker load and rejections.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Degraded check compares the enum to a string

1. **Nudge:** east-2 is the only worker that is degraded while traffic arrives. Does it ever look less attractive than east-1?
2. **Area:** Look at how effective_weight decides whether a worker is degraded.
3. **Exact:** `worker.state == "degraded"` is always False for an Enum; compare with `is WorkerState.DEGRADED`.

### B2: Request ending at the arrival time still counted as running

1. **Nudge:** Compare w01's end time with w02's arrival time.
2. **Area:** Look at how finished requests are dropped before routing.
3. **Exact:** release_finished keeps `end >= now_ms`; the spec wants `end > now_ms`.

### B3: Utilisation rounded before scaling to a percentage

1. **Nudge:** cen-1 shows 114.99999999999999. Where could the trailing 9s come from?
2. **Area:** Look at the order of rounding and multiplying in utilisation_pct.
3. **Exact:** Use round(100 * busy_ms / WINDOW_MS, 1).

### B4: Peak counter carried across workers

1. **Nudge:** Every central worker after cen-1 has the same peak as cen-1. Is that plausible for cen-4, which served nothing?
2. **Area:** Look at where peak and current are initialised in worker_stats.
3. **Exact:** Move `peak = 0` inside the per-worker loop, next to `current = 0`.

### B5: max_inflight 0 replaced by the default

1. **Nudge:** n02 and n06 should have nowhere to go. Which worker took them?
2. **Area:** Look at how the loader fills in max_inflight.
3. **Exact:** `item.get("max_inflight") or DEFAULT_MAX_INFLIGHT` turns 0 into 2; use item.get("max_inflight", DEFAULT_MAX_INFLIGHT).

### B6: Out-of-rotation filter always true

1. **Nudge:** Every worker is listed, including healthy ones. What does the filter evaluate to for a healthy worker?
2. **Area:** Read the condition in out_of_rotation operator by operator.
3. **Exact:** Compare w.state on both sides of the `or` (or use `w.state in (DOWN, DRAINING)`).

## "Why did that fix work?" probes

**B1**
- Why does `parse_state(...) == "degraded"` fail even though WorkerState.DEGRADED.value is "degraded"?
- Why were e01 to e04 still right with the comparison broken?

**B2**
- Why does only the west zone notice this?
- stats.peak_inflight has the same boundary rule. Where is it enforced there?

**B3**
- Why do 52.0 and 33.0 come out exact but 115.0 doesn't?
- Would round(x * 100, 1) after round(x, 3) be safe? Why or why not?

**B4**
- Why was `current` fine even though it is also a running counter?
- Which ordering of workers would have hidden this from the test?

**B5**
- cen-2 has no max_inflight at all. Why did it behave the same with and without the change?
- Why didn't any test on assignments notice north-2 taking traffic?

**B6**
- Why is WorkerState.DRAINING truthy on its own?
- Why does this only show up in the summary?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `relaymesh/health.py` → `apply_due`: The `<=` matches rule 1 (transitions at or before the arrival apply), and the cursor only moves forward because events are sorted by time in load_health.
- `relaymesh/stats.py` → `sweep_points`: Plain tuple sorting puts (t, -1) before (t, 1), so a request that ends exactly when another starts is counted as finished first, as the spec asks. It looks like it needs an explicit sort key, but it doesn't.
