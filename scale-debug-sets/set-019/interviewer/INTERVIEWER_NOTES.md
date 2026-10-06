# set-019 interviewer notes

**Scenario:** Replay a two-day on-sale log of hold/confirm/release events against a seat map. Holds last 10 minutes (inclusive) and confirms need an active hold by the same customer.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Customer ids only trimmed, not upper-cased

1. **Nudge:** B1, B3 and A6 were never sold. Find their hold and confirm rows in events.csv and compare them.
2. **Area:** Look at how customer ids are cleaned in the loader, compared with seat ids.
3. **Exact:** Use norm_id(row["customer"]) instead of clean(...).

### B2: Hold window made exclusive

1. **Nudge:** How long after E09 does E10 happen?
2. **Area:** Check is_active against replay rule 2.
3. **Exact:** Use <= HOLD_SECONDS.

### B3: Hold age ignores whole days

1. **Nudge:** C2 went to C10, whose hold was placed the day before. How old was that hold at E21?
2. **Area:** Look at how the age of a hold is computed.
3. **Exact:** Use total_seconds() instead of .seconds.

## "Why did that fix work?" probes

**B1**
- Why did the seat ids not have the same problem?
- Why did fixing this make a different seat (B3) stop selling?

**B2**
- Why was this hidden while customer ids weren't upper-cased?
- Which other events go through is_active, and why didn't they change?

**B3**
- What does timedelta(days=1, minutes=2).seconds return?
- Why do the other holds work fine with .seconds?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `boxoffice/booking.py` → `sort_events`: Sorting on (at, seq) looks like it could be just `at`, but seq is the file position, so events with the same timestamp (E01/E02) keep file order, as rule 1 requires. `at` is a parsed datetime, so the mixed formats sort correctly.
