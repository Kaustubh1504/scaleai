# set-091 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads sessions, members and holds from data/, splits the holds into live and expired with `holds.split_holds`, runs `allocation.allocate` on the live holds, and then builds the per-session lists, the expired list and the summary from `reports.summarize`.

### 2. Which holds does load_holds drop, and does it log them?

It skips any row whose `seats` is blank, whose cleaned session id is not in `sessions`, or whose cleaned member id is not in `members`. Nothing is logged; the rows simply never become Hold objects.

### 3. How does load_members read the tier column?

It calls `clean(row.get("tier")).lower()` and falls back to `"standard"` when that is empty. `clean` turns None into an empty string, so a missing key and a blank cell behave the same way.

### 4. What does read_rows return?

A list of dicts from `csv.DictReader`, one per data row, keyed by the header names exactly as they appear in the file after decoding.

### 5. In allocate(), what happens when a hold does not fit?

It is appended to the session's `waitlist` and the loop moves on to the next hold in priority order, so a later, smaller hold can still be booked.

### 6. How is top_member chosen?

`per_member` sums booked seats per member over all sessions, and `min` with key `(-seats, member_id)` picks the largest total, with ties going to the lowest member id.
