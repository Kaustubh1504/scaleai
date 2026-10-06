# set-023 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. Where is a task's pay computed?

pricing.task_pay looks up the rule for the task type in rates['task_types'], calls base_pay, then compares hours_between(assigned_at, submitted_at) with late_after_hours and applies late_factor with round() when it is larger.

### 2. What does hours_between return?

A float number of hours between two datetimes, computed from the difference `end - start` in utils.py.

### 3. Which tasks reach task_pay?

build_report keeps tasks whose cleaned status is 'accepted' and whose contributor_id is in the roster loaded by load_contributors.

### 4. How does the min payout default work?

load_contributors trims min_payout_usd_cents and uses DEFAULT_MIN_PAYOUT (1000) only if the trimmed text is empty; otherwise int() of the text, so '0' stays 0.

### 5. How is top_contributors built?

build_report fills a collections.Counter named counts while it loops over accepted tasks, then sorts counts.items() by (-count, id) and keeps the first three.

### 6. What shape does rates.json have?

A dict with late_after_hours, late_factor, currency_rates (currency -> rate, GBP stored as a string) and task_types (type -> either per_task_cents or hourly_cents).
