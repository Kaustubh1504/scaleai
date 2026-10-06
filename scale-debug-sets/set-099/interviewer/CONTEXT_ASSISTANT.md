# set-099 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does Broker.handle do for each event?

It calls `reap(ev.at)` first, then raises UnknownWorker if the worker isn't in `self.workers` (active workers only), otherwise dispatches to the method named by the action (`claim`, `heartbeat`, `ack`, `nack`). Any LeaseError is turned into a reason string via REJECTION_REASONS and appended to `self.rejected`.

### 2. What does _held check and raise?

UnknownTask if the task id isn't loaded; TaskClosed if the task status is 'done' or 'dead'; a plain LeaseError if there's no current lease for the task or it belongs to another worker. Otherwise it returns (task, lease).

### 3. How is the exception hierarchy laid out?

In models.py, LeaseError subclasses Exception, and UnknownTask, UnknownWorker and TaskClosed each subclass LeaseError directly.

### 4. What does reap do with an expired lease?

It removes the lease from `self.leases`, appends `[HH:MM:SS, worker, task_id]` to `self.expired`, and calls `_release`, which sets the task to 'dead' if attempts >= max_attempts and to 'pending' otherwise.

### 5. Where does first_claimed_at get set, and how is mean_ack_seconds built?

`claim` sets `task.first_claimed_at` only if it is still None. `reports.ack_times` collects `int(total_seconds())` of finished_at - first_claimed_at for done tasks, grouped by type, then reduces each list to a rounded mean.

### 6. Which workers end up in Broker.workers?

`loader.load_workers` keeps entries whose `active` is the JSON value true, or missing (it defaults to True), and maps the lower-cased id to a set of lower-cased types.
