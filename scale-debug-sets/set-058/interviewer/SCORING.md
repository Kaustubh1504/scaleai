# set-058 scoring sheet

Candidate: ________________   Date: ________   Interviewer: ________

| Bug | Found & fixed | Minutes | Hints used (0-3) | Explanation (1-4) |
|---|---|---|---|---|
| B1 Enterprise check compares the Plan enum to a string | ☐ | | | |
| B2 Request exactly 60 s old still counted in the window | ☐ | | | |
| B3 rpm_override 0 collapsed to None | ☐ | | | |
| B4 Credit keys trimmed but not lower-cased | ☐ | | | |
| B5 Overage part-cents floored instead of rounded up | ☐ | | | |
| B6 Top tenants sorted quietest first | ☐ | | | |

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

