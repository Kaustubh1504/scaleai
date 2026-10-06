# set-019 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does replay() do?

It creates a `BoxOffice` with the seat map, sorts the events with `sort_events`, and calls `office.apply(event)` for each one. `apply` dispatches on the action string to the `hold`, `confirm` or `release` method.

### 2. Where is a hold's age computed, and in what unit?

`booking.is_active` calls `utils.age_seconds(hold.held_at, now)` and compares the result with `HOLD_SECONDS`, which is 600.

### 3. What does BoxOffice keep track of?

`holds` (seat id → Hold with customer and held_at), `sold` (seat id → customer id) and `rejections` (a Counter of reason strings).

### 4. How are ids cleaned when the CSVs are loaded?

`load_seats` runs `norm_id` on seat ids. `load_events` builds each Event with `norm_id` for the seat and its own cleaning for the customer, and lower-cases the action.

### 5. When does confirm() reject an event?

When the seat is already in `sold`, when there is no active hold on the seat, or when the hold belongs to a different customer id. All three are counted as `no_hold`.

### 6. How are revenue and occupancy computed?

In `build_report`: revenue sums `seats[s].price` over sold seats and rounds to 2 decimals; occupancy is `100 * len(sold) / len(seats)` rounded to 1 decimal.
