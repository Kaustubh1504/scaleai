# set-016 interviewer notes

**Scenario:** Replay one night of a batch job scheduler: jobs run in rounds of `workers` by priority (higher number = more urgent), failed attempts are retried up to max_retries, dead jobs skip their dependents, and Test 3 summarises attempts and busy time.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Blank depends_on becomes a dependency on ""

1. **Nudge:** No job runs at all. Which jobs should be ready in round 1, and what do they depend on?
2. **Area:** Look at how depends_on is turned into a list of ids.
3. **Exact:** split_ids keeps empty parts; filter them with `if part.strip()`.

### B2: "false"/"no" parsed as enabled

1. **Nudge:** J12 and J13 show up in the rounds. What does jobs.csv say about them?
2. **Area:** Look at how the `enabled` column is interpreted.
3. **Exact:** parse_bool returns bool(text); it should return text.lower() in TRUTHY.

### B3: Priority sorted least urgent first

1. **Nudge:** Round 1 should start with J05 (priority 9). What does it start with?
2. **Area:** Look at the ordering of ready jobs in scheduler.py.
3. **Exact:** Sort by -j.priority, not j.priority.

### B4: One retry too many

1. **Nudge:** J05 has max_retries 0 but was attempted twice. How many attempts should it get?
2. **Area:** Look at how the code decides a failed job may run again.
3. **Exact:** can_retry should be retries_left > 0.

### B5: Skip cascade stops after the first dependent

1. **Nudge:** J10 depends only on J07, which is dead. Why is J10 still pending?
2. **Area:** Look at the function that marks dependents of a dead job.
3. **Exact:** Don't return inside the loop; extend `skipped` and keep scanning.

### B6: Mean attempts floored

1. **Nudge:** 13 attempts over 10 jobs is not 1.
2. **Area:** Look at how mean_attempts is computed.
3. **Exact:** Use / instead of //.

## "Why did that fix work?" probes

**B1**
- What does `"".split(";")` return, and why is it different from `"".split()`?
- Why does `all(...)` over an empty dependency list make a job ready?

**B2**
- Why does a blank `enabled` cell still count as enabled after the fix?
- Why did J12 and J13 jump to the front of the queue?

**B3**
- Why does J03 still run in the first rounds even though it has priority 3?
- How would you change this if the convention were 1 = most urgent?

**B4**
- Work through retries_left for J07 after each attempt. When should it hit zero?
- Why did J09 and J10 run while this was present?

**B5**
- Why was this invisible until the retry limit was fixed?
- Which other dead job went through this code, and why didn't it show the problem?

**B6**
- Why does round(..., 2) not save you here?
- What would `//` give for a negative total, and why does that matter in general?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `nightshift/utils.py` → `parse_timestamp`: The slash format is `%d/%m/%Y`, which looks swapped to anyone used to US dates, but the README says the slash format is day/month/year. It covers exactly the three listed formats.
