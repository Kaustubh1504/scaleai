# set-047 interviewer notes

**Scenario:** Per-task pay inside a half-open pay period plus spreadsheet-exported bonuses, minus a 2.5% fee rounded half-up, with a minimum payout that decides paid vs carried over.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Period end treated as inclusive

1. **Nudge:** C-01 is overpaid by exactly one transcribe task. Which one?
2. **Area:** Look at T-107's timestamp and the period end in period.json.
3. **Exact:** in_period uses `<= end`; README rule 2 says `< end`.

### B2: Byte order mark kept in the first header

1. **Nudge:** Every bonus is 0 and C-08/C-09 are missing. Is bonuses.csv being read at all?
2. **Area:** Print the keys of the first row the loader yields for bonuses.csv.
3. **Exact:** Open CSVs with encoding='utf-8-sig' in _rows.

### B3: Fee rounded with banker's rounding

1. **Nudge:** C-03's fee is 26 but 1060 × 2.5% is 26.5. What rule decides that?
2. **Area:** Look at how platform_fee rounds.
3. **Exact:** round() is half-to-even; use integer half-up: (gross * 250 + 5000) // 10000.

## "Why did that fix work?" probes

**B1**
- Why is T-101 (exactly at start) still paid?
- What would go wrong across two consecutive periods if both ends were inclusive?

**B2**
- Why did tasks.csv and rates.csv load fine through the same helper?
- Why didn't this raise a KeyError?

**B3**
- Why was C-04's fee (8.125) right either way?
- Why does doing the arithmetic in integer cents avoid float surprises?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `paycycle/utils.py` → `to_cents`: Multiplying a Decimal after quantize looks like it could leave fractions, but quantize to 0.01 guarantees a whole number of cents, it rounds half up as the spec says, and it strips `$` and thousands separators. Blank amounts return None so the loader can skip them.
