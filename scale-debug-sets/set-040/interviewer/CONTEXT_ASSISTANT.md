# set-040 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do?

It reads the worker count from config.json, loads jobs.csv and failures.csv, computes blocked jobs with dag.blocked_jobs, runs scheduler.simulate, and turns the JobStates into the jobs / events / blocked / summary sections.

### 2. How does simulate move through time?

`now` starts at the earliest release. Each step finishes running attempts with end <= now, adds newly ready jobs to `queue`, sorts it by Job.queue_key, starts queued jobs on free workers (lowest number first), then jumps to the next end time or future ready_at. When nothing is upcoming, any job still pending is marked skipped.

### 3. What does Job.queue_key return?

A tuple that sorts ascending: it starts with -priority so higher priorities come first, followed by the remaining tie-break fields.

### 4. How are failures and retries handled?

scheduler._finish checks whether the attempt number is in failures[job_id]. If it is, it logs fail@time and, when attempts <= max_retries, puts the job back to pending with ready_at = now + 10; otherwise the job is failed. Non-failing attempts log done@time and succeed.

### 5. What does JobState hold?

The Job, an events list, status, attempts, ready_at, start/end/worker of the latest attempt, and busy (minutes across all attempts). log() appends to events.

### 6. How does blocked_jobs pick a reason?

For each job it asks missing_dep for an unknown dependency; if one is found the reason is missing_dep:<id>. Otherwise, if the job is in cycle_members(jobs), the reason is cycle.

### 7. What shape is the team summary?

team_summary returns {team: {jobs, succeeded, busy_min}}, built by grouping JobStates with itertools.groupby keyed on job.team.
