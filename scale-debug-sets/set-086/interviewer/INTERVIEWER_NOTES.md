# set-086 interviewer notes

**Scenario:** Replay a request log through a smooth-weighted-round-robin balancer with fall/rise health checks, per-backend connection limits and sticky sessions that fail over. The report covers per-backend counts, nearest-rank median latency, zone totals and failovers.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: enabled=false backend joins the pool

1. **Nudge:** Where does b05 come from? Check its row in backends.csv.
2. **Area:** Look at how the `enabled` column is interpreted.
3. **Exact:** parse_flag should be `norm(value) in YES`.

### B2: Fail streak not reset by a passing check

1. **Nudge:** b02 never fails twice in a row in health.csv, yet it goes down. Why?
2. **Area:** Look at what a passing check does to a healthy backend's counters.
3. **Exact:** Restore `self.fails[bid] = 0` when a healthy backend passes.

### B3: Sticky check compares an Enum to a string

1. **Nudge:** Failovers are far higher than the single real one. Does any session ever stay on its backend?
2. **Area:** Look at the condition that decides whether the sticky backend can be reused.
3. **Exact:** Compare with `BackendState.HEALTHY` (as `usable` does), not the string "healthy".

### B4: Sticky reuse allowed at max_conns

1. **Nudge:** R07 is carol's second request, sent while R03 is still running. How many requests can b03 take?
2. **Area:** Look at the capacity check used when reusing a sticky backend.
3. **Exact:** has_room should be `active < backend.max_conns`.

### B5: Median takes the upper middle value

1. **Nudge:** Sort b01's durations by hand and find the 7th of 14.
2. **Area:** Look at the index p50 uses.
3. **Exact:** Use `ordered[math.ceil(0.5 * len(ordered)) - 1]`.

### B6: Counter.update on a zone string

1. **Nudge:** What are those single-letter keys in zones?
2. **Area:** Look at how each request is added to the zone Counter.
3. **Exact:** Use `zones[backends[bid].zone] += 1` (or update([zone])).

## "Why did that fix work?" probes

**B1**
- Why does s05 (blank enabled) stay out even with the bug?
- Why did a loader problem show up as a health transition?

**B2**
- The down state resets `passes` on a failure. Why is the healthy state the mirror image of that?
- Why did b02 come back at 18 s rather than 16 s?

**B3**
- Why does the report still print "healthy" as a string?
- How would `class BackendState(str, Enum)` have changed this behaviour?

**B4**
- Why was this invisible until the Enum comparison was fixed?
- Round robin eligibility uses a separate capacity check. Why did that one not need changing?

**B5**
- Why were b03 and b04 right with the bug?
- b02 also has an even count. Why didn't it change?

**B6**
- Why is the 'e' count equal to the total number of requests?
- Name another iterable that would quietly do the same thing in Counter.update.

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `lbreplay/loader.py` → `parse_offset`: A bare number is milliseconds and `s` multiplies by 1000, exactly as the README lists. `int(round(...))` avoids float truncation for values like 1.5s. It looks like a classic ms/s trap, but every format in the data is handled right.
- `lbreplay/balancer.py` → `pick`: This is the nginx smooth weighted round robin: add each eligible backend's weight, pick the highest current value (lowest id on ties), then subtract the total eligible weight from the winner. Subtracting the total, rather than the weight, is what keeps the sequence smooth.
