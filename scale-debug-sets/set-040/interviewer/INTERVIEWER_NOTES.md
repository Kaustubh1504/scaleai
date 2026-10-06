# set-040 interviewer notes

**Scenario:** Event-driven simulation of a day of batch jobs on 2 workers: priority queue (higher number first), dependencies, scripted failures with retries, blocked jobs (missing deps, cycles), and a per-team / lateness / utilization summary.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Queue modified while iterating it

1. **Nudge:** Two workers are free at 06:00 and m2 outranks m3. Why does m3 start first?
2. **Area:** Look at the loop that starts queued jobs. What happens to the list while it is being walked?
3. **Exact:** Iterate over a copy: for state in list(queue).

### B2: Release time missing from the queue tie-break

1. **Nudge:** At 13:42 one worker frees up. Which of a2 and a3 has waited longer?
2. **Area:** Look at the key the queue is sorted by.
3. **Exact:** Put self.release between priority and job_id.

### B3: Only the first dependency is checked

1. **Nudge:** b1 depends on m1 and zz-missing. Why isn't it blocked?
2. **Area:** Step through missing_dep for b1. How many dependencies does it look at?
3. **Exact:** Dedent `return None` so it runs after the loop.

### B4: Event log shared between all jobs

1. **Nudge:** m5's log contains starts on both workers and events from 13:00. Whose events are those?
2. **Area:** Where does each JobState's events list come from?
3. **Exact:** Default to None and create a new list per instance.

### B5: groupby over unsorted jobs

1. **Nudge:** etl has 6 jobs in jobs.csv. Which 2 did the summary count?
2. **Area:** What does groupby assume about its input order?
3. **Exact:** Sort by team before grouping.

### B6: Finishing exactly at the deadline counted as late

1. **Nudge:** When does a9 finish, and what is its deadline?
2. **Area:** Look at the comparison in late_jobs.
3. **Exact:** Use s.end > s.job.deadline.

## "Why did that fix work?" probes

**B1**
- Why doesn't the afternoon wave show the same problem?
- How else could you write this loop so that removal is safe?

**B2**
- Why does a6 still start at 14:12 either way?
- The docstring said 'earlier release' all along. How would you test the key directly?

**B3**
- Why does b1 end up 'skipped' instead of crashing the scheduler?
- Why is b2 still reported correctly?

**B4**
- Why does nothing else in the report change?
- Why isn't events=list() as a default any better?

**B5**
- How would you write this with a dict / defaultdict instead?
- Why can't you call len() on the group directly?

**B6**
- Which other comparisons in the package are boundary-sensitive?
- If deadlines had seconds, would anything change?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `jobsim/timeparse.py` → `parse_duration`: The regex makes both parts optional, which looks like it would accept an empty string, but `not any(match.groups())` rejects that. Bare digits are minutes (m4's '30'), and '1h' / '45m' / '1h30m' all parse to the right minute counts.
- `jobsim/dag.py` → `cycle_members`: A DFS with open/done states; meeting an 'open' node means the path from that node to here is a cycle, so path[path.index(dep):] is exactly the cycle (c1, c2). Unknown deps are skipped here because missing_dep reports them. c3 depends on the cycle but is not on it, so it is not blocked; it ends up skipped.
