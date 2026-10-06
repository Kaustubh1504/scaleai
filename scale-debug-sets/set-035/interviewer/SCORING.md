# set-035 scoring sheet

Candidate: ________________   Date: ________   Interviewer: ________

| Bug | Found & fixed | Minutes | Hints used (0-3) | Explanation (1-4) |
|---|---|---|---|---|
| B1 Counter.update on a model name counts its letters | ☐ | | | |
| B2 Round kept as text, so 10-12 sort before 2 | ☐ | | | |
| B3 Model with exactly the minimum games left off | ☐ | | | |

## Explanation quality

| Score | Meaning |
|---|---|
| 1 | Names the symptom only ("Test 2 fails"). |
| 2 | Symptom + location (file and function). |
| 3 | Symptom + location + why the code produces that output. |
| 4 | All of the above + the fix stated clearly, and why it does not break anything else. |

## Overall

- **Strong:** all 3 bugs fixed, ≤ 2 hints total, average explanation ≥ 3.
- **Pass:** ≥ 2 bugs fixed (all tests passing for that set requires all 3), ≤ 4 hints, average explanation ≥ 2.5.
- **Below bar:** fewer bugs, heavy hint use, or edits to tests/data/`# VERIFIED` code.

Notes:

