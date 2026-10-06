# set-048 interviewer notes

**Scenario:** Clean and dedupe samples, label each source group by majority vote, split groups (not samples) per label stratum with floor-rounded val/test counts, then cap train per label and report counts.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: exclude flag parsed with bool()

1. **Nudge:** S-004 and S-016 are listed as excluded. What does their exclude cell say?
2. **Area:** Look at how the exclude column is interpreted.
3. **Exact:** parse_flag returns bool(value); strings must be checked against TRUE_WORDS.

### B2: Duplicates detected on the raw id

1. **Nudge:** Both duplicate rows are lower-case versions of ids already in the file.
2. **Area:** Compare the id that is stored with the id that is checked against `seen`.
3. **Exact:** Use the normalised `sid` as the dedupe key, not clean(row['sample_id']).

### B3: groupby over unsorted samples

1. **Nudge:** g-07 has two cat samples and one dog sample. Why is it a dog group?
2. **Area:** Where are a group's samples collected before the majority vote?
3. **Exact:** groupby needs input sorted by the key: sort by group_id first.

### B4: Majority tie resolved by first seen

1. **Nudge:** Look at g-10's two samples. Is there a clear majority?
2. **Area:** How does majority() break ties?
3. **Exact:** most_common keeps insertion order on ties; use min(counts, key=lambda l: (-counts[l], l)).

### B5: Val slice end ignores the test offset

1. **Nudge:** Four groups are missing from group_split. What do they have in common?
2. **Area:** Look at the three slices in split_groups and where each starts and ends.
3. **Exact:** The val slice should be ordered[n_test:n_test + n_val].

### B6: All splits share one counts dict

1. **Nudge:** train, val and test show identical counts. Is that plausible?
2. **Area:** Check how the per-split dicts are created.
3. **Exact:** Use dict(empty) (a fresh copy) for each split.

## "Why did that fix work?" probes

**B1**
- Why did fixing this make the duplicates list change?
- Why are S-010 (`yes`) and S-036 (`1`) excluded either way?

**B2**
- Why was this invisible until the exclude flag was parsed properly?
- Why did a duplicate row change which split g-10 landed in?

**B3**
- Why were all the other groups right even with the unsorted input?
- Would collections.defaultdict(list) have avoided this?

**B4**
- Why did g-02 (cat, dog) come out right even with most_common?
- The comment says 'alphabetical among equals'. What does the code actually rely on?

**B5**
- Why didn't any group end up in two splits?
- With val_percent ≠ test_percent, what would this slice have done instead?

**B6**
- Why do the split member lists look fine while the counts don't?
- Would `{name: {**empty} ...}` or `copy.copy(empty)` also work? What about a nested dict?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `splitkit/splitter.py` → `apply_cap`: The `>=` check against the cap looks like it lets one too few through, but it runs before the increment, so exactly `cap` samples per label are kept. Sorting by (created_at, sample_id) is the spec's earliest-first order with id tie-break.
- `splitkit/utils.py` → `parse_timestamp`: It accepts exactly the four formats the README lists (two with time, two bare dates), with month/day order for the slash formats.
