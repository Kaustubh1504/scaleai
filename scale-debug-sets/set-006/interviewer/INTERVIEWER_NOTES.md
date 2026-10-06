# set-006 interviewer notes

**Scenario:** Replay an out-of-order event log through a claim/submit/approve/reject state machine with rework escalation at 3 rejections, then report per-person tables and queue-health numbers.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: History list shared by every task

1. **Nudge:** Every task reports the same number of transitions. What would make that happen?
2. **Area:** Look at where TaskRecord's history list is created.
3. **Exact:** `history = []` is a class attribute; create it in __init__ as `self.history = []`.

### B2: Same-time events ordered by id string

1. **Nudge:** T05 ends up claimed and E12 is listed as invalid. Look at E8 and E12 in events.csv.
2. **Area:** How are events with the same timestamp ordered?
3. **Exact:** Sort by `(ev.at, ev.seq)`; seq is the integer event number.

### B3: Review state compared to a string

1. **Nudge:** No task is ever approved or rejected. Which check do both actions share?
2. **Area:** Look at how `_reviewable` compares the task's state.
3. **Exact:** Compare against the enum: `task.state is not State.SUBMITTED`.

### B4: Any role can review

1. **Nudge:** Annotators appear in the reviewers table. Who decides who can review?
2. **Area:** Look at Member.can_review.
3. **Exact:** Write `self.role == "reviewer" or self.role == "lead"` (or `in ("reviewer", "lead")`).

### B5: Cycle time ignores whole days

1. **Nudge:** Which approved tasks took more than a day? Do their cycle times look right?
2. **Area:** Look at how cycle_hours turns a timedelta into hours.
3. **Exact:** Use `.total_seconds()` instead of `.seconds`.

### B6: First-pass count taken over all tasks

1. **Nudge:** A rate of 2.0 is impossible. Which side of the division is too big?
2. **Area:** Look at which collection first_pass is built from.
3. **Exact:** Filter `approved`, not `tasks.values()`.

## "Why did that fix work?" probes

**B1**
- Why are `state = State.QUEUED` and `rework = 0` safe as class attributes when `history = []` is not?
- What does `task.rework += 1` do to the class attribute, and why?

**B2**
- Why did other same-timestamp pairs (E33/E36, E34/E40) not change anything?
- Would zero-padding the ids in the data have hidden this? Why is that not a real fix?

**B3**
- Would this comparison have worked if State subclassed `str`?
- Why did avg_cycle_hours come out as None rather than a wrong number?

**B4**
- What value does the buggy expression return for an annotator?
- Why did E13 become invalid once E11 was accepted?

**B5**
- Why was this invisible while approvals were failing?
- What is `timedelta(days=2, hours=2).seconds`?

**B6**
- Why did this only show up after the review check was fixed?
- Why did Tests 1 and 2 never notice it?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `reviewflow/transitions.py` → `reject`: `rework >= MAX_REWORK` looks like it should be `>`, but the spec escalates when the rework count *reaches* 3, i.e. on the third rejection. T04 is rejected exactly three times and must end escalated.
- `reviewflow/loader.py` → `parse_when`: It tries exactly the three formats the README lists, with month/day order for the slash format, and raises on anything else.
