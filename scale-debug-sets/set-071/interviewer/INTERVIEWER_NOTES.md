# set-071 interviewer notes

**Scenario:** Turn a weekly work log, a manual adjustments sheet (saved with a byte-order mark) and a contributor roster into payout statements with tier percentages, half-up rounding, a minimum payout and carryover.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Byte-order mark kept in the first header

1. **Nudge:** The summary says all 10 adjustments are unmatched, yet the ids in the sheet look exactly like roster ids. What id does the loader actually read for each row?
2. **Area:** Print the header keys that _rows yields for adjustments.csv, with repr().
3. **Exact:** _rows opens the file with encoding='utf-8'; it needs 'utf-8-sig' so the byte-order mark is dropped.

### B2: Adjustment totals shared between contributors

1. **Nudge:** After B1, bonuses only ever grow as you go down the sorted contributor list. What would make one contributor's number include another's?
2. **Area:** Look at how adjustment_totals gets a fresh dict for each contributor.
3. **Exact:** The default `totals={...}` is shared across calls. Default to None and create the dict inside the function.

### B3: Every status treated as payable

1. **Nudge:** C01 shows 4 lines; count the C01 entries's entries that the spec says should be paid.
2. **Area:** Look at the status check in rules.py.
3. **Exact:** `status == "approved" or "auto-approved"` is always truthy. Use `status in ("approved", "auto-approved")`.

## "Why did that fix work?" probes

**B1**
- Why did contributors.csv and work_log.csv load fine through the same helper?
- Why doesn't the clean(k) on every header remove the mark?

**B2**
- Why was this invisible while every adjustment was unmatched?
- Why do the numbers in Test 2 differ from those in Test 1 with this one bug present?

**B3**
- What does `entry.status == "approved" or "auto-approved"` evaluate to for a rejected entry?
- Why did the qa-review entry for C09 still stay unpaid with this bug present?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `payrun/rules.py` → `in_period`: The `<` against midnight of end + 1 day looks like it drops the end date, but it is exactly what makes the whole end date (up to 23:59:59) count while 00:10 the next day does not. The spec says both dates are included in full.
- `payrun/rules.py` → `pct_of`: `(cents * pct + 50) // 100` looks like integer-division truncation, but adding 50 before dividing by 100 is integer half-up rounding. Replacing it with round() would use banker's rounding and turn C02's 544.5 into 544.
