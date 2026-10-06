# set-078 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does replay() do for each event, in order?

It sorts events by (ts, line). For each one it looks up the task (unknown → violation), calls _release_if_expired with the event time, checks actor_allowed, asks next_state for the target, checks the claim holder for approve/reject, then records a Transition and updates the task. After the loop it calls _release_if_expired on every task with settings['as_of'].

### 2. What does a Transition record, and where is claim_at taken from?

ts, task_id, actor, action, and claim_at, which is the task's claim_at at the moment the event is applied. For approve/reject that is the time of the claim_review being decided; for other actions it is usually None.

### 3. How does load_events treat duplicate rows?

It keeps a `seen` set of keys and skips any row whose key is already in it, so the first copy is kept. Line numbers come from enumerate(..., start=2), since the header is line 1.

### 4. Which tasks have open review claims near the end of the log?

T-10 (claimed by rv-02 at 2026-06-12 16:30) and T-12 (claimed by rv-03 at 17:00). With claim_ttl_minutes = 90, their deadlines are 18:00 and 18:30; as_of is 2026-06-12 18:00.

### 5. How does build_queue order and filter tasks?

It sorts every task in State.SUBMITTED by priority_key, then removes tasks whose project is in settings['paused'] (beta and delta in this data), and returns the ids.

### 6. How is review_minutes computed?

For each approve/reject transition that has claim_at, it gets or creates a ReviewTimer for the actor (dict.setdefault) and adds (ts - claim_at) in minutes. Each reviewer's value is ReviewTimer.mean(), rounded to 1 decimal.

### 7. Is State a str enum? How are states compared?

State is a plain enum.Enum with lower-case string values. The code compares with `is` (e.g. task.state is State.IN_REVIEW), and the report outputs state.value.
