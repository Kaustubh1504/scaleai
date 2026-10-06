# set-016 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads the config, then `load_jobs` (which drops disabled rows and normalises ids), then `load_outcomes`, runs `run_schedule` with `config.workers`, and finally builds `rounds`, the per-job table sorted by job id, and `summarize(jobs)`.

### 2. How does run_schedule decide when to stop?

Each iteration calls `ready_jobs(jobs)[:workers]`. If that batch is empty the loop breaks; otherwise every job in the batch gets one attempt via `run_attempt`, and if a job just became dead `skip_dependents` is called for it.

### 3. What does load_outcomes return, and what happens when there is no row for an attempt?

A dict keyed by `(job_id, attempt)` with the outcome trimmed and lower-cased. `run_attempt` looks the key up with a default of `"ok"`, so a missing row is a success.

### 4. What is retries_left?

A property on Job: `max_retries - (attempts - 1)`. It is read by `can_retry`, which `run_attempt` calls after a failed attempt.

### 5. Where is finished_round set?

In `run_attempt`, to the current round number, when the job becomes succeeded or dead. Skipped and pending jobs keep `None`.

### 6. What shape is depends_on on a Job?

A list of job id strings produced by `utils.split_ids` from the CSV cell, using `;` as the separator. `ready_jobs` checks each id against the set of succeeded job ids.

### 7. What does summarize count as a job that ran?

Jobs with `attempts > 0`. `total_attempts` and `busy_seconds` are summed over those jobs, and `counts` covers every loaded job.
