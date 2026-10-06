# set-051 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

`run()` loads tasks.csv and events.csv, creates a `Ledger`, calls `ledger.handle(event)` for each event in file order, then calls `ledger.reap(CLOSE_OF_DAY)` (2026-06-01 12:00). `build_report` then turns the ledger's lists and counters into the report dict.

### 2. What is in Ledger.active and what order is it in?

A list of `Lease` objects for leases currently held, appended in the order they were claimed. `ack` and `reap` remove entries from it; `holding()` scans it for a lease matching both task id and worker.

### 3. When is a lease considered expired?

`reap(now)` treats a lease as expired when `lease.expires_at <= now`. `_expire` then sets the task to dead if `attempts >= max_attempts`, otherwise pending, and adds one to `lost` for the lease's worker.

### 4. How are the id and name columns normalised by the loader?

`norm_task` trims and upper-cases, `norm_name` trims and lower-cases, and `clean` only trims (and turns None into an empty string). `load_tasks` and `load_events` each choose one of these per column.

### 5. What does a heartbeat change when it is accepted?

It sets `lease.expires_at` to the heartbeat time plus `LEASE_LENGTH` (10 minutes) and adds one to both `lease.extensions` and `task.extensions`. A rejected heartbeat appends to `ledger.rejected` and changes nothing else.

### 6. Where does the workers table come from?

`worker_table` takes every worker that appears in `ledger.claims`. `claims` counts their claims with a non-null task, `acks` comes from the `acks` Counter (incremented in `ack`), and `lost` from the `lost` Counter (incremented in `_expire`).
