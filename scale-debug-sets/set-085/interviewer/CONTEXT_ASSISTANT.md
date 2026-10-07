# set-085 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() call, in order?

`load_accounts`, `load_deposits`, `load_logins`, then `build_rings` and `ring_index`, `self_referrals`, `qualifying_accounts` and `bonus_ledger` (counted per referrer). It then walks `referrals(accounts)` sorted by referrer id, builds flags with `has_burst` on each referrer's signup times, and computes the summary from the rows that are not held.

### 2. How does build_rings decide which accounts to join?

It groups account ids by key: `("device", device)` for each account with a device, and `("ip", ip)` for each login whose IP is not in the shared-network set. Every id in a group is unioned with the group's first id. Groups of 2+ after `find` become rings, each sorted, ordered by size descending then first id.

### 3. What does load_accounts do with a referred_by that isn't in the file?

It collects the cleaned ids of all rows first, and sets `referred_by` to None when the cleaned referrer is not among them. acc-30's `acc-99` becomes None.

### 4. What does has_burst receive and how does it check the window?

A list of signup datetimes for one referrer's referred accounts. It sorts them and, for each run of 3 consecutive signups, calls `minutes_between(first, third)` and returns True if any is <= 60.

### 5. In what order does bonus_ledger look at deposits, and what does it skip?

By `(deposited_at, deposit_id)`. It skips deposits whose account has no referrer, is a self-referral, or is in the `paid` set, and deposits that fail `is_qualifying`. Each remaining deposit appends `(referrer, account, deposit_id)`.

### 6. How is the `qualifying` count in a report row computed?

From `qualifying_accounts`, a set of referred account ids with at least one deposit passing `is_qualifying`; the row counts how many of the referrer's referred accounts are in that set. It is independent of `bonus_ledger`.

### 7. Which deposits and logins does the loader drop?

Deposits whose cleaned account id is unknown (d18 for acc-41) or whose amount is blank (d21). Logins whose cleaned account is unknown (acc-41) or whose IP is blank. Status is stored trimmed and lower-cased.
