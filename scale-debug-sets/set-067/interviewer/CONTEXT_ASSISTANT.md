# set-067 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. In what order are requests handled?

load_requests parses every row and returns them sorted by ts with Python's stable sort, so equal timestamps keep file order. reports.run then calls Venue.handle on each request in that order.

### 2. What does Venue.handle do before it looks at the action?

It calls expire(req.ts), which walks a copy of self.holds and frees every hold whose age is at least HOLD_TTL_S (900 seconds), then removes it from self.holds.

### 3. How does best_available pick seats?

It takes seats in the requested section whose status is 'available', sorts them by (seat.row, seat.number), returns None if fewer than quantity remain, and otherwise returns the first quantity seats.

### 4. What are the possible outcomes for a request?

hold → held, duplicate (customer already has an active hold) or rejected (not enough seats); confirm → confirmed or no_hold; release/cancel → released or noop; anything else → ignored. They are stored in Venue.statuses.

### 5. Where do held_seats and the sales numbers come from?

Venue._hold records the labels of the picked seats in held_seats under the request id. build_report counts seats whose final status is 'sold', prices them with the PRICES table by tier, and groups by section.

### 6. Why does ben's confirm R05 come out no_hold?

Ben's hold R02 is at 09:04 and R05 is at 09:19, exactly 900 seconds later. expire runs first with `age >= HOLD_TTL_S`, so the hold is freed before _confirm looks for it.
