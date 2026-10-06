# set-064 interviewer notes

**Scenario:** Simulate an overnight batch run minute by minute: per-queue slots, priority 1 most urgent, same-queue dependencies, scripted failures retried up to max_retries with linear backoff. Report each job's timeline, wait and lateness.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Priority order reversed

1. **Nudge:** etl-3 has priority 3. Should it be the first etl job to run?
2. **Area:** Check dispatch_order against rule 3 of the README.
3. **Exact:** Drop the minus sign: sort by (j.priority, j.submitted_at, j.job_id).

### B2: One retry too few

1. **Nudge:** trn-1 has max_retries 2 and succeeds on attempt 3. How many attempts does it get?
2. **Area:** Look at the condition that decides whether a failed job is retried.
3. **Exact:** should_retry uses `<`; the spec allows a retry while n ≤ max_retries.

### B3: Dependency ids only trimmed

1. **Nudge:** rpt-1 finished at 00:45. Why did rpt-2 never start?
2. **Area:** Compare how job ids and dependency ids are normalised in the loader.
3. **Exact:** Use norm_id(d) for depends_on, not d.strip().

### B4: Wait uses timedelta.seconds

1. **Nudge:** ops-1 was submitted on May 2. How long had it waited by 00:00 on May 4?
2. **Area:** Look at how minutes_between turns a timedelta into minutes.
3. **Exact:** Use total_seconds(), not .seconds.

### B5: Queue logs share one default list

1. **Nudge:** etl and ops report the same count, and it is far more than the 16 jobs could run. Where could the extra entries come from?
2. **Area:** Look at how QueueLog gets its entries list.
3. **Exact:** Use `entries=None` and create a new list inside __init__.

### B6: Finishing on the deadline counted as late

1. **Nudge:** Compare ops-1's finish time with its deadline.
2. **Area:** Look at the comparison in is_late.
3. **Exact:** Use finished_at > deadline.

## "Why did that fix work?" probes

**B1**
- Why didn't the ops, reports or training timelines change?
- The comment says 'most urgent first'. What does 'most urgent' mean in this repo?

**B2**
- Why did ops-3 (max_retries 3, one failure) still get its retry?
- Why does fixing this also change trn-2?

**B3**
- Why did rpt-4 run fine even though it also has dependencies?
- What would deps_done return if a dependency named a job in another queue?

**B4**
- Why were all the other wait times right?
- What would `.seconds` give for a negative timedelta of one minute?

**B5**
- Why does the count change depending on how many tests ran before this one?
- Why didn't the per-job attempt counts change?

**B6**
- Why does only ops-1 change?
- Which test data would you add to pin down this boundary?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `nightshift/retry.py` → `next_ready_at`: Rule 5 asks for backoff_min × n after the n-th failed attempt, and the dispatcher passes job.attempts, which already counts the failed attempt. Multiplying by the attempt number looks like it should be an exponent or n-1, but linear backoff is exactly what the spec says.
