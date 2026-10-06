# set-096 interviewer notes

**Scenario:** Three text datasets are cleaned (blocked licenses, incomplete rows, quality floor), deduped by normalised text, then whole source documents are assigned to train/val/test by largest deficit against floor-based targets, with per-dataset pins and fraction overrides merged onto shared defaults.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Blocked samples removed while iterating

1. **Nudge:** TX-08's source is proprietary. Why wasn't that the reason it was dropped?
2. **Area:** Look at how drop_blocked walks the list while it removes from it.
3. **Exact:** `for sample in samples:` mutates the list being iterated; iterate over a copy: `for sample in list(samples):`.

### B2: Duplicate original chosen by id before date

1. **Nudge:** Compare the created dates of IN-03 and IN-11.
2. **Area:** Look at how dedupe chooses which copy to keep.
3. **Exact:** pick_original's key has its fields swapped: use (s.created, s.sample_id).

### B3: Deficit ties broken alphabetically

1. **Nudge:** Work through intent's assignment by hand: what are the deficits when in-d04 is placed?
2. **Area:** Look at how choose_split breaks ties between splits.
3. **Exact:** `max(SPLITS, key=lambda split: (deficit[split], split))` prefers 'val' over 'train'; use `key=lambda split: deficit[split]` so the first split in SPLITS order wins.

### B4: Pin keys trimmed but not lower-cased

1. **Nudge:** Look at how the toxicity pin is written in datasets.json.
2. **Area:** Compare how pin keys and sample doc ids are normalised.
3. **Exact:** load_datasets builds pin keys with textnorm.clean(doc); use textnorm.norm_doc(doc).

### B5: Shallow copy of defaults leaks fractions

1. **Nudge:** Summaries has no fraction override. Where could a 30% test share come from?
2. **Area:** Look at how merge copies the defaults before applying a dataset's keys.
3. **Exact:** copy.copy(defaults) shares the nested fractions dict; use copy.deepcopy(defaults).

### B6: groupby over unsorted labels

1. **Nudge:** The totals don't even add up to `kept`. What would produce numbers that small?
2. **Area:** Look at how label_totals groups samples.
3. **Exact:** groupby needs sorted input: `ordered = sorted(samples, key=lambda s: s.label)`.

## "Why did that fix work?" probes

**B1**
- Why did only TX-08 get the wrong reason, when IN-05, IN-14 and TX-16 were also blocked?
- Why didn't kept counts or split assignments change at all?

**B2**
- Why did the toxicity and summaries pairs come out right even with this key?
- Why does choosing the other copy not move any document between splits?

**B3**
- Why does a val/test tie or a train/test tie still come out right with this key?
- Why does one tie change four documents' splits?

**B4**
- Why did the intent pin keep working?
- How would you change the code so an unmatched pin is noticed instead of silently ignored?

**B5**
- Why were intent's targets unaffected even though it uses the same defaults?
- Would `{**defaults}` have fixed it? Why or why not?

**B6**
- Why does the dict end up with the last run's length rather than the first?
- What simpler standard-library tool would avoid this whole class of mistake?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `holdout/allocator.py` → `compute_targets`: The `//` looks like an integer-division slip, but rule 6 asks for floor(n x pct / 100) with whole-number percentages, so multiplying first and floor-dividing by 100 is exact. Train takes the remainder, so the targets always add up to n.
- `holdout/textnorm.py` → `fingerprint`: Stripping every non-word, non-space character looks aggressive, but rule 4 says duplicates match ignoring case, punctuation and runs of whitespace. Lower-casing, removing punctuation and re-joining on single spaces is exactly that.
