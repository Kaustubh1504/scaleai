# set-032 interviewer notes

**Scenario:** Three vendors deliver sentiment labels as a BOM-prefixed CSV, a plain CSV and JSON. Rows are validated, copies of the same task are merged (latest wins, ties go to the most trusted vendor, tags unioned), and Test 3 summarises labels, tags and batches.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Zero duration treated as missing

1. **Nudge:** Look at acme row 3 in the data. Which rule could reject it?
2. **Area:** Check how validate.py decides a duration is missing.
3. **Exact:** `if not rec.duration_s` also catches 0. Use `if rec.duration_s is None`.

### B2: Equal-time tie goes to the least trusted vendor

1. **Nudge:** T008 was submitted by acme and brightlabel at the same minute. Which vendor should win per the README?
2. **Area:** Look at the key merge() uses to pick the winning copy.
3. **Exact:** rank returns (submitted, priority); it should be (submitted, -priority).

### B3: Merged tags not de-duplicated

1. **Nudge:** T001 has 'sentiment' twice. Where are tags from the copies combined?
2. **Area:** Look at merge() in dedupe.py.
3. **Exact:** Sort a set comprehension, not a generator: sorted({tag for ...}).

### B4: Vendor label maps share one dict

1. **Nudge:** T024 came from cortex with label 'mixed'. Does cortex's label_map mention 'mixed'?
2. **Area:** Look at how each vendor's settings are built from the defaults in config.py.
3. **Exact:** copy.copy shares label_map between vendors; use copy.deepcopy(defaults).

### B5: Removing tags from the list being iterated

1. **Nudge:** Where does 'tmp:review' come from, and why wasn't 'tmp:qa' left in too?
2. **Area:** Look at the loop in split_tags that drops blank and internal tags.
3. **Exact:** Iterate over a copy (`for tag in list(tags):`) or build a new list with a comprehension.

### B6: BOM kept in the first CSV header

1. **Nudge:** Every acme winner is in 'unbatched'. Print the keys of one acme row.
2. **Area:** Look at how CSV files are opened in loader.py.
3. **Exact:** Open CSVs with encoding="utf-8-sig" so the BOM is stripped.

## "Why did that fix work?" probes

**B1**
- Why did the T003 record not change even though one of its copies was rejected?
- Which other values would `not x` treat as missing that a `None` check would not?

**B2**
- Why does the comment in rank() not help you here?
- If two copies from the same vendor had the same timestamp, which would win and why?

**B3**
- Why did tag_counts in the summary stay correct while this was present?
- Why didn't single-copy records show repeated tags?

**B4**
- Why didn't the priorities leak between vendors the same way?
- Would `dict(defaults)` have fixed it? Why or why not?

**B5**
- Why were single tmp: tags (T018, T029) removed correctly?
- Why didn't this show up in any record test?

**B6**
- Why did only the batch field break, and not task_id or email?
- Why did brightlabel.csv load fine with the same code?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `vendorfeed/utils.py` → `parse_timestamp`: The `%d.%m.%Y` format looks like it swaps day and month compared with the slash format, but the README says dotted dates are day.month.year and slash dates are month/day/year. Returning None for unparseable values is intentional: validation turns None into bad_timestamp.
