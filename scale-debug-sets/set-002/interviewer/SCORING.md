# set-002 scoring sheet

Candidate: ________________   Date: ________   Interviewer: ________

| Bug | Found & fixed | Minutes | Hints used (0-3) | Explanation (1-4) |
|---|---|---|---|---|
| B1 "false"/"no" strings parsed as active | ☐ | | | |
| B2 Annotation annotator ids not lower-cased | ☐ | | | |
| B3 Zero accuracy replaced by the prior | ☐ | | | |
| B4 Exactly 0.5 accuracy blocked | ☐ | | | |
| B5 Weight ties resolved by insertion order | ☐ | | | |
| B6 Label counts include unresolved tasks | ☐ | | | |

## Explanation quality

| Score | Meaning |
|---|---|
| 1 | Names the symptom only ("Test 2 fails"). |
| 2 | Symptom + location (file and function). |
| 3 | Symptom + location + why the code produces that output. |
| 4 | All of the above + the fix stated clearly, and why it does not break anything else. |

## Overall

- **Strong:** all 6 bugs fixed, ≤ 2 hints total, average explanation ≥ 3.
- **Pass:** ≥ 5 bugs fixed (all tests passing for that set requires all 6), ≤ 4 hints, average explanation ≥ 2.5.
- **Below bar:** fewer bugs, heavy hint use, or edits to tests/data/`# VERIFIED` code.

Notes:

