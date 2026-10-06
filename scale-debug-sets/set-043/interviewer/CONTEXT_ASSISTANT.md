# set-043 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. How does replay() process the events?

It builds a `Ledger` from the sessions and calls `ledger.apply(ev)` for each event in file order. `apply` checks unknown session and `closed` first, then dispatches to `hold`, `confirm`, `cancel` or `comp` by the action name and stores the outcome in `ledger.outcomes`.

### 2. Where are holds stored, and when are they removed?

`Ledger.holds` is a dict keyed by `(session_id, attendee)`. `confirm` pops the hold for its key, and `cancel` pops it if there is no active booking. Expired holds aren't deleted on their own; `held()` and `hold()` call `is_expired` to skip them.

### 3. What does Ledger.taken count?

The seats of bookings for that session whose status is in `OCCUPYING` (`confirmed`, `comped`). Holds are counted separately by `held()`.

### 4. How are ids cleaned on load?

`load_sessions` keys sessions by `norm_session` (trim + upper). `load_events` sets `action` and `attendee` with `clean(...).lower()` and builds `session_id` from the row on the `session_id=` line. A blank seats cell becomes 1.

### 5. What does is_expired compare?

It takes `now - hold.held_at` (a timedelta), converts it to a number of seconds and checks whether that is greater than `HOLD_SECONDS` (600).

### 6. What feeds the attendees section of the report?

`attendee_seats(ledger.bookings)`, which loops over all bookings (including cancelled ones), applies a status condition and sums seats per attendee into a Counter, returned as a sorted dict.
