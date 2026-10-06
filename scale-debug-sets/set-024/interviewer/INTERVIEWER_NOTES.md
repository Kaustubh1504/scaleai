# set-024 interviewer notes

**Scenario:** Clean a labeled feedback export (blank labels, withdrawn consent, excluded tags, whitespace/case duplicates), split by document using pinned test docs plus an MD5 bucket, draw a capped per-label validation sample, and report per-split stats. Test 3 checks the test-split report.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Any non-blank consent string counts as consent

1. **Nudge:** I013 and I026 are missing from excluded. Look at their consent column.
2. **Area:** How is the consent text turned into a boolean?
3. **Exact:** parse_bool returns bool(text); it should return text in {"y", "yes", "true", "1"}.

### B2: Duplicate tie on created date not broken by item id

1. **Nudge:** The duplicate list has I016 where I030 was expected. Compare the two rows.
2. **Area:** Both rows have the same date once parsed. What decides which one is kept?
3. **Exact:** pick_keeper's key should be (it.created, it.item_id).

### B3: doc_id not lower-cased

1. **Nudge:** doc_splits has two extra keys. Where do they come from in items.csv?
2. **Area:** Look at how doc ids are cleaned when items are loaded.
3. **Exact:** load_items needs clean(row['doc_id']).lower().

### B4: Validation sample takes cap + 1 per label

1. **Nudge:** Count the ids per label in val_sample and compare with val_cap_per_label.
2. **Area:** Look at the check that decides whether another item fits.
3. **Exact:** val_sample should use len(bucket) < cap.

### B5: Label tally shares a default dict

1. **Nudge:** The test split has 6 rows, but its label counts add up to far more.
2. **Area:** Look at the helper that counts labels. What happens to its dict between calls?
3. **Exact:** tally's default must be None, not {}.

### B6: Token total not reset per split

1. **Nudge:** An average of almost 19 words for six short comments? Count a few by hand.
2. **Area:** Where does the token total for a split start from?
3. **Exact:** Move tokens = 0 inside the for-split loop.

## "Why did that fix work?" probes

**B1**
- Why did I018 and I022 stay excluded?
- Why did blank consent (I003) still behave correctly?

**B2**
- Why was the I012/I025 pair unaffected?
- Why does it matter that the date strings are in different formats here?

**B3**
- Nothing leaked into val or test with this data. Why is it still a real problem?
- Why does the bucket change when only the case of the id changes?

**B4**
- Why did neutral come out right?
- How would you write this with a slice instead of a counter check?

**B5**
- Why did the numbers change depending on how many tests ran before?
- Why didn't the `if counts is None` line protect against this?

**B6**
- Which split's avg_tokens was still right, and why?
- Would summing with sum(it.tokens for it in members) have avoided this?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `splitkit/splitter.py` → `split_for`: The `< 70` / `< 85` boundaries look like they could be off by one, but buckets 0-69 are exactly 70 values for train, 70-84 are 15 for val and 85-99 are 15 for test, as rule 5 says. Pinned docs are checked first.
- `splitkit/utils.py` → `parse_date`: It handles exactly the three README formats, with month/day/year for the slash format, and returns a date so comparisons across formats work.
