# set-038 interviewer notes

**Scenario:** Replays a request log through a weighted least-connections balancer with connection caps, disabled backends, sticky clients and health probes (down after 2 consecutive failures), then reports per-backend load and pool totals.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Health strings read with bool()

1. **Nudge:** api-3 failed probes at 1000 and 1100 ms. Is it still getting traffic after that?
2. **Area:** Print the probes load_probes returns. What is healthy for the 'no' row?
3. **Exact:** Use parse_bool(row["healthy"]).

### B2: Load ratio uses floor division

1. **Nudge:** R02 arrives while api-1 has one connection and api-2 has none. Why does api-1 win?
2. **Area:** Compute load_of for api-1 with one open connection.
3. **Exact:** Use true division: len(backend.active) / backend.weight.

### B3: Failure count not reset by a healthy probe

1. **Nudge:** Look at api-2's probes in health.csv. Should it be down at 1500 ms?
2. **Area:** What does a healthy probe do to backend.fails?
3. **Exact:** Set backend.fails = 0 in the healthy branch.

### B4: Connections ending exactly at arrival kept open

1. **Nudge:** R05 holds st-1 from 350 to 2000. R15 arrives at 2000. Is st-1 free?
2. **Area:** Look at which connections release_finished keeps.
3. **Exact:** Keep only connections with end > now_ms.

### B5: Zero-length requests given the default duration

1. **Nudge:** R06 has duration 0. How long does the simulation think it lasts?
2. **Area:** Look at how load_requests applies the default duration.
3. **Exact:** Pass the default into parse_ms instead of using `or`.

### B6: by_pool counts rejected requests

1. **Nudge:** Add up by_pool and compare it with routed.
2. **Area:** Which list does the Counter iterate?
3. **Exact:** Count over routed, not requests.

## "Why did that fix work?" probes

**B1**
- Why doesn't the same mistake break `enabled`?
- Which of the probe strings in health.csv would bool() get right?

**B2**
- Why does bt-3 end up serving nothing?
- If weights could be 0, what would you do in load_of?

**B3**
- Why couldn't you see this until the probe parsing was fixed?
- Which test would you add to pin down 'consecutive'?

**B4**
- Why does R27 get routed when this is wrong, and rejected when it is right?
- How would you represent a connection so this boundary is explicit?

**B5**
- Where else in the loader would `or` with a default be dangerous?
- Why does R11 move to bt-3 with this mistake in place?

**B6**
- Why does no test in Test 1 or Test 2 notice?
- What invariant check would catch this immediately?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `lbsim/balancer.py` → `pick`: Checking the sticky id before `if not options` looks out of order, but the loop over an empty list simply does nothing, and the sticky backend is only honoured if it is in the candidate list (enabled, healthy, below its cap). The key (load, -weight, id) is exactly the README order: lowest load, then higher weight, then id.
