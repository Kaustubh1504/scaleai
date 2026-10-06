# set-047 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does _rows yield?

For each CSV data row it yields a dict whose keys are the header names passed through clean() and lower-cased; values are the raw strings. It is used for rates, tasks and bonuses.

### 2. How does base_earnings decide whether a task is paid?

It skips task ids it has already seen, then skips tasks whose status isn't `approved` or whose type isn't in the rates table, then checks `in_period(completed_at, period)`. Paid tasks add their rate in cents to the contributor's total.

### 3. What do the period values look like after load_period?

`start` and `end` are datetimes (bare dates become midnight), `fee_percent` is a float (2.5), and `min_payout_cents` is an int (2000).

### 4. Which contributors appear in lines?

The union of contributor ids with task earnings and ids with bonuses, sorted. A contributor with only bonuses gets base_cents 0.

### 5. How does to_cents handle '$1,000.00' or a blank?

It strips `$` and commas, returns None for a blank string, otherwise quantizes the Decimal to 0.01 with ROUND_HALF_UP and multiplies by 100, returning an int.

### 6. What does platform_fee return for a given gross?

An int number of cents computed from gross_cents and fee_percent; build_statement subtracts it from gross to get net.
