# set-095 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow in build_report?

It loads the period, roster, rates and work log, filters the work with earnings.payable_entries, builds statements with build_statements (which also takes the loaded adjustments), then computes flags with audit.audit_flags, the payout lines with payout_lines and the summary with summarize.

### 2. What does load_adjustments return?

A list of (contributor_id, Decimal amount) tuples, one per entry in adjustments.json, with the id passed through clean() and the amount through parse_amount.

### 3. How does build_statements use the adjustments?

It sums the amounts into a defaultdict keyed by the id from each tuple, then for every roster id (sorted) reads that dict with the roster id; ids that are not roster ids are never read.

### 4. What does audit_flags group on?

It groups the entries it is passed by contributor_id and then by project, collecting duration_ms values; reasons_for takes each project's median, divides by 1000 and compares it with the project's min_seconds.

### 5. Which entries does build_report keep in the local variables work and entries?

work is the full parsed work log from load_work; entries is the result of payable_entries(work, contributors, rates, period).

### 6. How is the payout file ordered?

payout_lines collects the Contributor objects whose statement status is paid and sorts them with key=lambda c: c.account_no, using whatever value load_contributors stored in account_no.

### 7. What shape does the work log have?

40 rows with entry_id, contributor_id, project, submitted_at (three date formats), duration_ms and status; ids and statuses come in mixed case, and one row (w40) belongs to C-11, who is not on the roster.
