# set-013 interviewer notes

**Scenario:** Scan a day of captioning submissions: reject rows with bad timestamps, flag annotators whose share of sub-20-second submissions is at least 0.5, and flag annotators who gave the same normalised answer as a different annotator on a task.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Submission annotator ids not lower-cased

1. **Nudge:** ann-04 has five rows in the CSV. How many does the report count, and which are missing?
2. **Area:** Compare how annotator ids are cleaned in load_registry and in load_submissions.
3. **Exact:** Use norm_annotator(row["annotator_id"]) in load_submissions.

### B2: Rejected submissions silently dropped

1. **Nudge:** s13 has a timestamp with no seconds. Where should it show up in the report?
2. **Area:** Look at what the except block in load_submissions does with the row.
3. **Exact:** Append row["submission_id"].strip() to rejected before `continue`.

### B3: Same annotator resubmitting counted as copying

1. **Nudge:** Who is ann-06 supposed to have copied on T4?
2. **Area:** Look at how copy_tasks counts the annotators that share an answer.
3. **Exact:** Build `who` as a set: {s.annotator_id for s in group}.

## "Why did that fix work?" probes

**B1**
- Why did ann-03 and ann-08 (mixed case in annotators.csv) work fine?
- After this fix, s13 is still missing from the rejected list. What does that tell you about where to look next?

**B2**
- Why was this invisible until ann-04's ids were normalised?
- What would have made this failure loud instead of silent?

**B3**
- Why does the `found` accumulation still work once `who` is a set?
- Should the resubmission itself be a separate signal? How would you add it without breaking this rule?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `fraudscan/timing.py` → `is_fast`: `<` looks like a boundary slip, but the spec says under 20 seconds is fast and exactly 20 is not. ann-07's 20-second submission confirms it. The duration uses total_seconds(), not .seconds.
- `fraudscan/copying.py` → `norm_answer`: split()/join collapses every run of whitespace and trims the ends, lower() handles case, and rstrip('.!?') drops trailing punctuation, exactly as README rule 4 says.
