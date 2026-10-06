# set-037 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do?

It loads transactions.csv (getting loaded transactions sorted by timestamp plus a rejected list), cards.json and rates.json, then calls engine.score_all to get one Decision per scored transaction. It returns decisions, rejected and a summary.

### 2. How does load_transactions decide a row is rejected?

It calls parse_row for each CSV row. parse_row raises MissingFieldError (a ValueError subclass carrying .field) for the first blank required field, and parse_amount/parse_timestamp raise plain ValueError for text they can't parse. load_transactions catches these and appends {txn_id, reason}.

### 3. How is velocity tracked?

Each card has a CardState with a deque `recent` of timestamps. velocity_hit removes timestamps from the left that are too old compared with the current transaction, appends the current timestamp, and returns True if 3 or more remain.

### 4. Where does currency conversion happen and what if a rate is missing?

evaluate calls money.to_usd first. to_usd looks the code up in the rates dict, raises UnknownCurrencyError(currency) if it is absent, and otherwise returns amount * rate rounded to 2 decimals.

### 5. Where is the daily limit checked?

In rules.evaluate: it adds the USD amount to state.spend_by_day[txn.ts.date()] and adds the over_limit flag if the running total is above the card's daily_limit_usd.

### 6. Which cards have notable data?

c02 has three transactions between 09:00 and 09:10; c03 has three foreign (FR) transactions within 5 minutes; c04 crosses its 1000 USD limit with its third transaction; c05 has a ZAR transaction, and ZAR is not in rates.json.
