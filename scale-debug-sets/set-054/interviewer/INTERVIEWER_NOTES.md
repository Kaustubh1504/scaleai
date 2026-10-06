# set-054 interviewer notes

**Scenario:** Replay claim/pass/request_changes/reject/resubmit events through a two-level review state machine with conflict-of-interest rules, then report history, the waiting queue (higher priority first), reviewer stats and cycle times. Test 3 is the summary.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Broad except clause catches conflicts first

1. **Nudge:** The right events are refused, only the reason is off. Which exception does a conflict raise?
2. **Area:** Look at the class hierarchy in models.py and the order of the except clauses in handle().
3. **Exact:** Put `except ConflictOfInterest` before `except AssignmentError`.

### B2: History list shared by every task

1. **Nudge:** Every task's history is the same long list. Where does each task get its list?
2. **Area:** Look at the class-level attributes on Task and which of them are mutated rather than reassigned.
3. **Exact:** Create the list per instance: self.history = [] in __init__ (and drop the class attribute).

### B3: reverse=True also reverses the tie-breaks

1. **Nudge:** T2 and T10 are in the right places. Look at the three priority-2 tasks.
2. **Area:** Check the sort key and direction in waiting_queue against the README's queue rule.
3. **Exact:** Negate priority and drop reverse=True: key=lambda t: (-t.priority, t.entered_at, t.task_id).

### B4: Actor names only trimmed

1. **Nudge:** There's a 'Dana' and a 'dana' in the reviewer table. Should there be?
2. **Area:** Compare how people are normalised in load_tasks and load_events.
3. **Exact:** Use norm_person(row["actor"]) for the actor.

### B5: timedelta.seconds drops whole days

1. **Nudge:** Only T3 is off, and it's the only cycle longer than a day.
2. **Area:** Look at how elapsed time is turned into hours in metrics.py.
3. **Exact:** Use elapsed.total_seconds() instead of elapsed.seconds.

### B6: Enum state compared to a string

1. **Nudge:** by_state says 4 approved, yet approval_rate is 0.0.
2. **Area:** Compare how by_state and approved read the state in summarize().
3. **Exact:** Compare with State.APPROVED (or use t.state.value == 'approved').

## "Why did that fix work?" probes

**B1**
- Why are the other reasons (unknown_task, invalid_transition) unaffected?
- How could the hierarchy be designed so the clause order matters less?

**B2**
- Why are state, revision and l1_reviewer safe as class-level defaults when history isn't?
- Why didn't states or cycle times change?

**B3**
- Why does negating just the priority fix it?
- Why should T7 (submitted earliest) come after T11 and T12?

**B4**
- Which data would turn this into a real security problem for the four-eyes rule?
- Why did the state machine still accept all of Dana's actions on T3?

**B5**
- What are timedelta's three stored components?
- Why did T8 (23.7 h) still come out right?

**B6**
- Would making State subclass str change this? What are the trade-offs?
- Why didn't the rejected count have the same problem?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `reviewflow/loader.py` → `parse_time`: It tries exactly the three formats in the README, month/day for the slash form, and raises on anything else rather than guessing.
- `reviewflow/machine.py` → `check_claim`: Authors can never claim, and the level-1 reviewer is only blocked at level 2. Both raise ConflictOfInterest, which is a subclass of AssignmentError, so the handler has to catch it first.
