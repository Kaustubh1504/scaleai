# set-008 interviewer notes

**Scenario:** Read three vendor roster exports (two CSVs, one with a BOM, and a JSON file), validate and clean each row, merge duplicate contributors by email with a latest-update-wins rule, and summarise loads and rejections.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: BOM kept in the first header

1. **Nudge:** Only vendor_a sources lose their reference. What is different about that file?
2. **Area:** Print the column names read_csv sees for vendor_a.csv.
3. **Exact:** Open CSVs with encoding="utf-8-sig".

### B2: Merged skills keep repeats

1. **Nudge:** Only merged contributors have repeated skills. Where are rows combined?
2. **Area:** Look at how merge_duplicates builds skills.
3. **Exact:** Use a set comprehension `{...}` inside sorted().

### B3: Defaults copied shallowly

1. **Nudge:** Every record has the same long notes list. Where is each record's notes list created?
2. **Area:** Look at how build_record starts a new record from DEFAULTS.
3. **Exact:** Use copy.deepcopy(DEFAULTS) (or build fresh lists).

### B4: Day rate floor-divided

1. **Nudge:** Only kai@lab.io's rate is off, by half a unit. How is it written in vendor_b.csv?
2. **Area:** Look at the `/day` branch of parse_rate.
3. **Exact:** Use true division: `/ 8`.

### B5: Reason lookup checks the base class first

1. **Nudge:** No row is reported as missing_field, yet three rows have no email. Where is the reason chosen?
2. **Area:** Look at the order of REASONS and the class hierarchy in schema.py.
3. **Exact:** Put (MissingField, "missing_field") before (ValueError, "invalid_value").

### B6: Country aliases looked up before upper-casing

1. **Nudge:** The countries summary has lower-case and long-form keys. Where are country values cleaned?
2. **Area:** Look at norm_country in schema.py.
3. **Exact:** Upper-case the code before the alias lookup.

## "Why did that fix work?" probes

**B1**
- Why didn't `str.strip()` in _norm_keys clean the header?
- Why were all the other vendor_a columns fine?

**B2**
- Why does kai@lab.io pass even with the bug?
- What is the difference between `sorted({...})` and `sorted(...)` here?

**B3**
- Why are `skills` and `sources` unaffected even though DEFAULTS has a list for skills too?
- What does `DEFAULTS["notes"]` contain after a run with the shallow copy?

**B4**
- What type does `156.0 // 8` return, and why is the float type no protection here?
- Why does rounding to 2 decimals not hide this?

**B5**
- How is this the same mistake as ordering `except ValueError:` before `except MissingField:`?
- Why does test_rejected_rows pass with this bug?

**B6**
- Why did `USA` (quinn) still map to US?
- Why did vik end up as UNKNOWN either way?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `rosterload/dedupe.py` → `newer`: The `>=` looks like it lets an older row win, but the tuple includes the read order, so it only matters on an exact tie, where README rule 13 says the later row wins (femi: vendor_b replaces vendor_a).
- `rosterload/normalize.py` → `parse_date`: It accepts exactly the three formats in README rule 4 and raises RowError (a ValueError) otherwise, so bad dates become invalid_value.
