# set-088 interviewer notes

**Scenario:** Simulate a day of a batch cluster minute by minute: four worker pools, priority 5 = most urgent, dependencies, scripted attempt failures with linear retry backoff. The report covers makespan, pool slots/utilisation and the longest wait (including a backlog job from two days earlier).

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Dependency ids not upper-cased

1. **Nudge:** G03 has no dependencies in the intake, but jobs.csv lists one. What is different about how it is written?
2. **Area:** Follow depends_on from the CSV through parse_deps and resolve_deps.
3. **Exact:** parse_deps should apply norm_job to each piece, not just strip().

### B2: Least urgent job dispatched first

1. **Nudge:** C02 is the most urgent job but starts last. What decides dispatch order?
2. **Area:** Read queue_key and README rule 7 together. Don't trust the comment.
3. **Exact:** queue_key should return (-job.priority, ...).

### B3: One retry too few

1. **Nudge:** I01 has max_retries 1 and attempts.csv says its second attempt is ok. How many attempts did it get?
2. **Area:** Look at the retry decision after a failed attempt.
3. **Exact:** should_retry should be `attempts <= max_retries`.

### B4: max_retries 0 replaced by the default

1. **Nudge:** G02 failed in both versions. What else in its row is different?
2. **Area:** How many times may G02 run according to jobs.csv and README rule 8? Where is that value read?
3. **Exact:** In load_jobs, use `int(retries) if retries else DEFAULT_RETRIES` so 0 stays 0.

### B5: Wait loses whole days

1. **Nudge:** M01 was submitted two days before day_start. How long did it wait, and what does the report say instead?
2. **Area:** Look at how the wait is converted to minutes.
3. **Exact:** Use total_seconds() instead of .seconds in wait_minutes.

### B6: Inactive workers counted as slots

1. **Nudge:** cpu shows 4 slots, but the schedule only ever used w01 and w02.
2. **Area:** The report and the scheduler work out slots in different places. Compare them.
3. **Exact:** capacity() needs `if w.active`.

## "Why did that fix work?" probes

**B1**
- Why did G03 still start after G01 even with the dependency gone?
- What data change would turn this into a visible scheduling difference?

**B2**
- Why did the mem, io and gpu lanes come out the same with this bug?
- cpu busy minutes and makespan didn't change. Why?

**B3**
- Why is I02's state `blocked` rather than `failed` or `pending`?
- G02 also fails. Why did its result not change with this bug?

**B4**
- The test is in the schedule file, but the cause is in the loader. How did you trace it back?
- Why didn't G02's extra attempts change the makespan?

**B5**
- For what kinds of wait does `.seconds` give the right answer?
- Why didn't the simulation itself suffer from the same problem for M01?

**B6**
- Why did the schedule tests pass even though slot counting was off?
- io has the same count with or without the filter. Why?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `batchsched/timeutil.py` → `parse_duration`: The regex accepts a number with an optional h/m/s unit. `// 60` on seconds looks lossy, but every seconds value in the data is a whole number of minutes, and the spec says everything is in whole minutes. A bare number is minutes, as the README says.
- `batchsched/retry.py` → `backoff_delay`: Backoff is linear by spec (`retry_backoff × attempts made so far`), so `base * attempts` is right even though exponential backoff is what most people expect.
