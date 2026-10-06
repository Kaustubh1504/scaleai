# set-091 interviewer notes

**Scenario:** Settle a day of seat holds: a hold is live if confirmed within 15 minutes (inclusive), live holds are booked per session by tier (gold 3 > silver 2 > standard 1, higher wins) then time, and what doesn't fit is waitlisted. Test 2 reports seats left, fill rate and top member.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: members.csv read without stripping the BOM

1. **Nudge:** In A2, gold member m-07 lost out to two standard members. What tier does the code think m-07 has?
2. **Area:** Print the keys of one row read from members.csv. The README mentions something special about that file.
3. **Exact:** read_rows opens with encoding="utf-8"; it needs "utf-8-sig" so the byte-order mark is dropped from the first header.

### B2: Confirmation at exactly 15 minutes treated as late

1. **Nudge:** Compare H08 and H10 in holds.csv. How long after placing was each one confirmed?
2. **Area:** Look at the comparison against the deadline in holds.py, next to README rule 1.
3. **Exact:** is_confirmed uses `<`; it should be `hold.confirmed_at <= deadline`.

### B3: Counter subtraction drops sold-out sessions

1. **Nudge:** Which sessions are missing from seats_left, and what do they have in common?
2. **Area:** Look at how seats_left is built from the two Counters in reports.py.
3. **Exact:** `capacity - booked` drops counts <= 0. Build it per session: {sid: capacity[sid] - booked[sid] for sid in sorted(capacity)}.

## "Why did that fix work?" probes

**B1**
- Why did sessions.csv and holds.csv load fine through the same helper?
- Why did the code not crash, even though the tier column could not be found? Would row["tier"] have been better here?

**B2**
- Why didn't B1's booked list or seats_left change when H08 expired?
- The H08 timestamps are in two different formats. Did that matter here, and how would you rule it out?

**B3**
- What would `capacity - booked` do if a session were overbooked (negative seats left)?
- Why do total_booked and fill_rate still come out right?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `seatbook/allocation.py` → `priority_key`: The minus on the rank looks like a flipped priority, but sorting ascending on -rank puts the highest rank (gold, 3) first, which is what the spec wants because the higher number is more important. Then earliest placed_at, then hold_id.
- `seatbook/loader.py` → `parse_when`: The `%d.%m.%Y` format looks like a day/month swap, but the README says the dotted format is day.month.year. It covers exactly the three listed formats and returns None for a blank cell.
