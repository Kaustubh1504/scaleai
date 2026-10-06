# set-043 interviewer notes

**Scenario:** Replay a hold/confirm/cancel/comp event log against workshop capacities, with 10-minute hold expiry, then report occupancy and per-attendee seats.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Hold age read with timedelta.seconds

1. **Nudge:** E35 confirms a hold placed the previous afternoon. How old is it?
2. **Area:** Look at how is_expired measures the hold's age.
3. **Exact:** Use (now - hold.held_at).total_seconds(), not .seconds.

### B2: Event session ids upper-cased but not trimmed

1. **Nudge:** E17 says unknown_session, but WS-09 exists. Look at the raw row.
2. **Area:** Compare how session ids are cleaned in load_sessions and in load_events.
3. **Exact:** Use norm_session(row["session_id"]) in load_events.

### B3: Cancelled bookings counted in attendee seats

1. **Nudge:** dev@lab.io cancelled, yet shows 3 seats.
2. **Area:** Look at the status filter in attendee_seats.
3. **Exact:** Write `b.status in ("confirmed", "comped")` (or compare b.status twice).

## "Why did that fix work?" probes

**B1**
- Why did E05 (12 minutes) still expire correctly?
- Why didn't WS-07's occupancy in the report change?

**B2**
- Why did ws-01 and ws-05 events work even with this change?
- Why did no occupancy number change?

**B3**
- Why are the session `taken` numbers still right?
- What would `b.status == ("confirmed" or "comped")` do instead?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `seatbook/engine.py` → `has_room`: `left - seats >= 0` is the same as seats <= left, which is rule 2 (in use + requested at most capacity). E02 fills WS-01 exactly and is accepted, as it should be.
