# set-067 interviewer notes

**Scenario:** Replay a box-office request log: holds pick the best available seats, expire after 15 minutes, and are confirmed, released or ignored. Test 2 checks sales and request outcomes.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Seat numbers kept as strings

1. **Nudge:** R01 asked for 4 seats in an empty orchestra and got A1, A10, A11, A12. What order were the seats sorted in?
2. **Area:** best_available is VERIFIED, so look at what it is given: the type of Seat.number.
3. **Exact:** load_seats stores clean(row['number']); store int(row['number']).

### B2: Hold age read from timedelta.seconds

1. **Nudge:** R17 (erin) gets BALC-A3/A4 although dora's hold on A1/A2 is from the previous day.
2. **Area:** Look at how expire() measures a hold's age.
3. **Exact:** Use (now - hold.held_at).total_seconds(), not .seconds.

### B3: Release branch condition always true

1. **Nudge:** R08 (upgrade) and R20 (refund) are not in the ignored list. What outcome did they get?
2. **Area:** Look at the branch in handle() that routes release and cancel.
3. **Exact:** Write `req.action == 'release' or req.action == 'cancel'` (or `in ('release', 'cancel')`).

## "Why did that fix work?" probes

**B1**
- Why did the balcony and orchestra row B holds come out right?
- Why did sold counts and revenue not change?

**B2**
- Why did all the same-day expiries (ben at 09:19) still work?
- Why does dora's R21 confirm still come out no_hold?

**B3**
- What would have happened if gus or lee had an active hold at the time?
- Why didn't hold and confirm requests fall into the release branch?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `seatbook/booking.py` → `best_available`: It filters to available seats in the section, sorts by (row, number) and refuses partial holds with `len(free) < quantity`. The slice [:quantity] is exact. It is only as good as the types it is given: if number were a string, the sort would be lexicographic, but that would be a loader problem, not this function's.
