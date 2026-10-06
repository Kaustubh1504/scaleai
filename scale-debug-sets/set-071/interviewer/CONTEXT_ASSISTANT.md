# set-071 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads rates.json, the roster, the work log and the adjustments through loader.py, calls ledger.build_statements to get one Statement per active contributor plus the unmatched-adjustment count, then reports.settle computes paid and carry_forward for each statement before the summary is assembled.

### 2. What does loader._rows yield?

One dict per CSV row. Keys are the header names passed through clean() and lower(); values are the cells passed through clean(). It is used for all three CSV files.

### 3. How does load_entries handle repeated entry ids?

It stores entries in a dict keyed by the normalised entry id, so a later row with the same id replaces the earlier one. The result is the dict's values, in first-seen key order.

### 4. Which entries does build_statements count toward earned?

Those for which rules.counts_toward_pay is true: is_payable(entry), the task type is a key of rates['task_types'], and in_period(completed_at, start, end). Each counted entry adds 1 to lines and line_amount(...) to earned.

### 5. How are bonus and clawback filled in on a Statement?

build_statements groups adjustments by contributor id (ids not in the roster increment `unmatched`), then calls adjustment_totals(extras.get(cid, [])) for each active contributor and copies the 'bonus' and 'clawback' values from the returned dict.

### 6. How is line_amount computed?

units × the task type's cents per unit, passed to pct_of together with the tier percentage from rates['tiers'].

### 7. What decides whether a statement is paid?

reports.settle: if statement.gross >= rates['min_payout'] (2000) the gross is paid, otherwise paid is 0 and carry_forward is the gross.
