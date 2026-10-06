# set-002 interviewer notes

**Scenario:** Score annotators on gold tasks, block the inaccurate ones, then resolve every other task by accuracy-weighted vote with an alphabetical tie-break. Test 3 summarises the resolved labels.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: "false"/"no" strings parsed as active

1. **Nudge:** Two annotators in the table shouldn't be there. Look up their entries in annotators.json.
2. **Area:** Look at how the `active` field is interpreted.
3. **Exact:** parse_bool returns bool(value). Strings need value.strip().lower() in {"true","yes","y","1"}.

### B2: Annotation annotator ids not lower-cased

1. **Nudge:** ann-05 answered two gold tasks in the CSV, yet gold_answered is 0. Where did those rows go?
2. **Area:** Compare how annotator ids are normalised in load_annotators and in read_annotations.
3. **Exact:** read_annotations uses clean(); it should use norm_annotator().

### B3: Zero accuracy replaced by the prior

1. **Nudge:** ann-05 answered both gold tasks wrong. What accuracy should they have?
2. **Area:** Look at where the prior is applied in gold.py.
3. **Exact:** `rates.get(aid) or PRIOR` turns 0.0 into 0.5. Use rates.get(aid, PRIOR).

### B4: Exactly 0.5 accuracy blocked

1. **Nudge:** Which annotators are blocked, and what do their accuracies have in common?
2. **Area:** Check the blocking rule in voting.py against README rule 5.
3. **Exact:** is_blocked uses <=; it should be row.accuracy < MIN_ACCURACY.

### B5: Weight ties resolved by insertion order

1. **Nudge:** Look at T03's votes and weights. Is there a clear winner?
2. **Area:** Look at how the winner is chosen when totals are equal.
3. **Exact:** pick_winner uses max(totals, key=totals.get). Use min(totals, key=lambda l: (-totals[l], l)).

### B6: Label counts include unresolved tasks

1. **Nudge:** Where does the None key in label_counts come from?
2. **Area:** Look at which collection summarize counts over.
3. **Exact:** Count over `resolved`, not results.values().

## "Why did that fix work?" probes

**B1**
- Why did ann-10 (active: 0) stay inactive even with the broken function?
- Why does fixing this also change T05's confidence?

**B2**
- Why didn't Test 2 change when ann-05's annotations were silently dropped?
- Which loader rule threw these rows away, and was that rule itself correct?

**B3**
- Why was this invisible while annotator ids weren't normalised?
- Name another value besides 0.0 that `or` would wrongly replace in code like this.

**B4**
- Why did this also block an annotator who answered no gold at all?
- How would you test the boundary so a regression like this is caught on its own?

**B5**
- Why did T10 come out right even with this bug?
- The comment says 'alphabetical on ties'. What does that tell you about trusting comments in this round?

**B6**
- If the code had filtered with `if r.label` instead of the status, would that be equivalent? When could they differ?
- Why did Tests 1 and 2 never notice this?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `consensus/loader.py` → `latest_submissions`: The `>=` looks like it should be `>`, but the spec says that on equal timestamps the later row in the file wins, so a later row with the same time has to replace the earlier one. It compares parsed datetimes, so the mixed formats sort correctly.
- `consensus/utils.py` → `parse_timestamp`: It covers exactly the three formats the README lists, with month/day order for the slash format.
