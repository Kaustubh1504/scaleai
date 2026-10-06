# set-003 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do from start to finish?

It loads the tasks into a `Broker`, calls `broker.handle(event)` for every event in file order, calls `broker.reap(AS_OF)` once at the end (AS_OF = 2026-04-02 12:00), and then formats the dispatch log, per-task status and attempts, dead letters, rejections and completion counts.

### 2. Why does pick_next sort twice?

It sorts by `(created_at, id)` first, then sorts the result by `priority` with `reverse=True`. Python's sort is stable, so tasks with equal priority keep the created_at/id order from the first pass. It returns the first element, or `None` if nothing is pending.

### 3. Where and when are expired leases handled?

In `Broker.reap(now)`. `handle()` calls it before every event, and `build_report` calls it once more at AS_OF. For each lease it considers expired (compared against `LEASE_SECONDS` = 900), it deletes the lease and sets the task to `dead` or `pending` depending on `Task.exhausted()`.

### 4. When does a task's attempts counter go up?

Only in `Broker.lease`, when a task is handed out. Expiry and completion never change it.

### 5. What happens on a complete from a worker who doesn't hold the lease?

`Broker.complete` appends `(time, worker, task_id)` to `rejected` and returns `False`. The task and the lease are left untouched. The same thing happens for unknown task ids like A-999.

### 6. How does the loader handle a blank max_attempts?

`load_tasks` uses `DEFAULT_MAX_ATTEMPTS` (3) when the stripped cell is empty, and `int(...)` otherwise.

### 7. Which timestamp formats does parse_ts accept?

`%Y-%m-%d %H:%M:%S`, `%Y-%m-%d %H:%M`, `%m/%d/%Y %H:%M` and `%Y-%m-%dT%H:%M:%S`, tried in that order. Anything else raises ValueError.
