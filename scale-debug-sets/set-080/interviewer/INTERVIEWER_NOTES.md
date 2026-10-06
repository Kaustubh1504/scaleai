# set-080 interviewer notes

**Scenario:** Two CSV vendor exports (one with a UTF-8 BOM) and a JSON dump are validated row by row, inactive people are dropped, and duplicates are merged by email (latest update wins, source priority 1 breaks ties, skills unioned). The roster is then exported as JSON. Test 3 checks summary counts and the exported timestamps.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: CSV opened without BOM handling

1. **Nudge:** Every vendor_a row is rejected as missing email, yet the file plainly has emails. Print the keys of one parsed row.
2. **Area:** Look at how read_csv_source opens the file, and at the first bytes of vendor_a.csv.
3. **Exact:** Open CSVs with encoding="utf-8-sig".

### B2: String 'FALSE' treated as active

1. **Nudge:** After the encoding fix, ben and leo appear in the roster. What does their `active` cell say?
2. **Area:** Look at how parse_active treats string values.
3. **Exact:** Restore the string branch: value.strip().lower() in TRUTHY.

### B3: Merged skills not de-duplicated

1. **Nudge:** Which contributors have a skill listed twice? What do they have in common?
2. **Area:** Look at how merge combines skills across a person's rows.
3. **Exact:** Use a set comprehension inside sorted(): sorted({s for r in group for s in r.skills}).

### B4: Blank skill entries kept after split

1. **Nudge:** Some contributors have a skill that is an empty string. Look at their raw skills cells.
2. **Area:** What does str.split return for an empty string or a trailing separator?
3. **Exact:** Filter out blanks: `... for s in items if text(s)`.

### B5: Timestamp ties go to the least trusted source

1. **Nudge:** cara's name and country come from vendor_c. Compare the two cara rows: which fields are equal?
2. **Area:** Check how pick_winner breaks a tie, against the priority convention in sources.json.
3. **Exact:** Use -r.priority in the key (or min with a reversed date).

### B6: Export serialises datetimes with str()

1. **Nudge:** The exported timestamps have a space where the spec has a 'T'. What turns a datetime into a string here?
2. **Area:** Look at the `default` argument of json.dumps in export_roster.
3. **Exact:** Pass default=_encode.

## "Why did that fix work?" probes

**B1**
- Why was only the first column affected?
- Why is utf-8-sig safe for files that have no BOM?

**B2**
- Why couldn't you see this until vendor_a rows were being read?
- Why did vic (vendor_c, active: false) stay inactive the whole time?

**B3**
- Why were single-source contributors unaffected?
- Is `sources` safe from the same issue? Why?

**B4**
- Why did zoe (a JSON empty list) not get an empty skill?
- What would "".split() (no argument) have returned instead?

**B5**
- Why did kim only show this problem once vendor_a was read correctly?
- Why do mixed timestamp formats (2026-01-20T10:00:00 vs 2026-01-20 10:00) still tie here?

**B6**
- Why does default=str 'work' without raising, and why is that dangerous?
- What would default=str do to a set?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `rosterflow/normalize.py` → `clean_email`: Stripping 'mailto:' looks like it might mangle addresses, but the README requires it, and only a leading prefix is removed. Lower-casing the whole address is also what the spec asks for.
- `rosterflow/serialize.py` → `_encode`: It turns datetimes into isoformat() strings and sets into sorted lists, and raises TypeError for anything else, which is what json's `default` hook is supposed to do. It only works if it is actually passed as `default`.
