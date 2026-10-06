# set-064 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads the config, the jobs (with deadlines placed on the run day) and the scripted outcomes. Then, for each queue name in sorted order, it calls `run_queue` with that queue's jobs and slot count and keeps the returned QueueLog. Job rows and the summary are built after every queue has run.

### 2. How does run_queue decide what to start each minute?

It first completes running attempts whose finish time is at or before the current minute, looking up each outcome by `(job_id, attempts)`. Then it builds the ready list (pending, `ready_at <= now`, `deps_done`), sorts it with `dispatch_order` and starts as many as there are free slots.

### 3. When is job.attempts incremented relative to should_retry?

It is incremented when an attempt starts. So when a failed attempt completes and `should_retry(job)` runs, `job.attempts` already includes that failed attempt.

### 4. What does deps_done check?

That every id in `job.depends_on` is a key in `by_id` (the jobs of the same queue) and that job's status is `done`.

### 5. Where do wait_min values come from?

`report.wait_minutes` returns None if the job never started, otherwise `timeutil.minutes_between(job.submitted_at, job.first_start)`. `first_start` is set the first time the job is dispatched.

### 6. What is QueueLog used for?

`run_queue` creates one per queue and calls `record(job_id, attempt, outcome)` each time an attempt completes. The summary's `attempts_by_queue` is the length of each log's `entries` list.

### 7. How are deadlines parsed?

`parse_deadline` splits `HH:MM` and replaces the hour and minute on `run_start`, so every deadline is on the run day. A blank cell gives None, and is_late treats None as no deadline.
