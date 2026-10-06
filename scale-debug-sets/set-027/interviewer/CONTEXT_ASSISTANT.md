# set-027 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens for each event in Broker.handle?

It first calls `reap(event.ts_ms)`, makes sure a Worker object exists for the worker id, formats the time as HH:MM:SS, and then branches on the action: `lease` picks a task with `pick_next`, `heartbeat` moves the deadline if `holds()` is true, and `ack` marks the task done and calls `worker.record` if `holds()` is true.

### 2. What does holds(event) check?

That there is a lease stored for `event.task_id` and that its `worker_id` equals the event's worker. It doesn't look at the deadline itself; expired leases have already been removed by `reap`.

### 3. What units are times stored in?

Everything is converted by `loader.to_ms` to integer epoch milliseconds in UTC. `LEASE_MS` is 60_000. `fmt_ms` turns ms back into an HH:MM:SS string for the logs.

### 4. Where is first_leased_ms set?

In the `lease` branch of `Broker.handle`, only when it is still None, so it keeps the time of a task's first lease even if the task is leased again later.

### 5. How is completed_by built?

`build_report` loops over `broker.workers` sorted by id and emits `list(w.completed)` for each worker whose `completed` is non-empty.

### 6. When is a task dead-lettered?

Only inside `reap`: when a lease is removed, the task becomes `dead` if `attempts >= max_attempts`, otherwise `pending`. A final reap runs at END_OF_LOG after all events.
