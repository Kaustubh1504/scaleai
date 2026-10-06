# set-088 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside simulate() at each minute?

First every running attempt whose end equals t is finished in job-id order: its worker is released, a Run is recorded, and the outcome from attempts.csv (default `ok`) decides succeeded / retry / failed. Then queued jobs with a failed or blocked dependency are marked blocked (repeated until nothing changes). Finally eligible jobs are sorted with queue_key and each takes `table.free_worker(pool)` if there is one.

### 2. Where are job submission times turned into simulation minutes?

In simulate: `submit[job.id] = max(0, to_offset(day_start, job.submitted_at))`. to_offset uses total_seconds() // 60, so a job submitted before day_start is clamped to minute 0.

### 3. What does load_jobs do with depends_on?

Each row's depends_on string goes through `parse_deps`, which splits on ';' and skips blank pieces. After all rows are read, `resolve_deps` removes any id that is not one of the accepted job ids, and the jobs are rebuilt with the filtered tuple.

### 4. How is the retry backoff applied?

When an attempt fails and should_retry(attempts, max_retries) is true, the job goes back to `queued` with `ready_at = t + backoff_delay(attempts, backoff)`; config `retry_backoff` '300s' parses to 5 minutes.

### 5. Which workers can PoolTable hand out?

Its constructor keeps only workers with `active` True, sorted by id. free_worker returns the first one in the requested pool that is not in `busy`.

### 6. Where does the report's slots number come from?

pool_report calls `capacity(workers)` from pools.py on the full worker list loaded from workers.csv, and indexes it by each name from pool_names.

### 7. How is longest_wait chosen?

For every job that has a first_start, wait_minutes converts first_start back to a datetime and subtracts submitted_at. The minimum by (-minutes, job id) is returned as {job, minutes}.
