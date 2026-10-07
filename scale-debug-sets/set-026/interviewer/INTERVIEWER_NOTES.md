# set-026 interviewer notes

**Scenario:** Per-project batches of tone labels are deduped, resolved to agreed/escalated/pending against each project's quorum and agreement bar, then scored per annotator and summarised per project and per team (roster CSV has a BOM).

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Resubmissions with a changed label not collapsed

1. **Nudge:** Pick E-06 and count its rows in email.csv by annotator. Who appears twice, and what differs between their rows?
2. **Area:** C-04 also has a repeat annotator but its count is right. Look at what latest_per_annotator treats as the same submission.
3. **Exact:** The dedupe key is `(ann.task_id, ann.annotator_id, ann.label)`; it should be `(ann.task_id, ann.annotator_id)`.

### B2: Exactly min_votes treated as too few

1. **Nudge:** Compare the vote counts of the tasks that went to pending with each project's min_votes.
2. **Area:** Look at the quorum check in resolve().
3. **Exact:** `len(labels) <= project.min_votes` should be `<`.

### B3: Skips counted as disagreeing votes

1. **Nudge:** Only a06 and a08 are off. What else do they have in common in the table?
2. **Area:** Trace a skip row through agreement_table's loop.
3. **Exact:** After `skips[aid] += 1` the loop must `continue`.

### B4: Zero agreement reported as None

1. **Nudge:** a10 has agreed_tasks 4 but no agreement value. Is that consistent with rule 7?
2. **Area:** Look at how the rate is formatted for the report.
3. **Exact:** Use `if row.rate is not None`.

### B5: Per-project label counts accumulate

1. **Nudge:** The overall counts are right but per-project counts keep growing. What do the two paths share?
2. **Area:** Look at count_labels' signature.
3. **Exact:** Default `counts=None` and create the Counter inside the function.

### B6: Roster read without stripping the BOM

1. **Nudge:** The roster loads with no members. Print the keys of the first row read_rows returns for teams.csv.
2. **Area:** Compare how teams.csv is decoded with what the README says about it.
3. **Exact:** Open with encoding="utf-8-sig".

## "Why did that fix work?" probes

**B1**
- Why did C-04 come out right while E-06 did not?
- Which submission of a11's on E-06 should count, and how does the README decide?

**B2**
- Why did no agreed label change even though three tasks changed status?
- Which data row would you add to make this change agreement rates too?

**B3**
- Why are a02's numbers right even though a02 also skipped a task?
- Why do skip counts still come out right?

**B4**
- Why does a11 still correctly show None?
- Where else in this repo could a 0 be confused with missing?

**B5**
- Why does running test_3 alone give different numbers from running the whole suite?
- Why is `overall` unaffected?

**B6**
- Why didn't `.strip()` on the header remove the mark?
- Why were the batch CSVs unaffected even though they use the same reader?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `tonevote/consensus.py` → `decide`: The `>=` looks like it might need to be `>`, but README rule 5 says a share at or above the bar is agreed (C-01 is exactly 3/4 = 0.75). The explicit tie check implements rule 4, so R-01's 2-2 split escalates even though 0.5 meets the reviews bar.
- `tonevote/utils.py` → `parse_timestamp`: The day.month.year format looks like it clashes with month/day/year, but the separators differ (`.` vs `/`), so each string matches exactly one format, and both are listed in the README.
