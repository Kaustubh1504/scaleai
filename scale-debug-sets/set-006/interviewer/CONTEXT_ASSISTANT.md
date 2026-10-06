# set-006 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads members.json, tasks.csv and events.csv through loader.py, calls `engine.replay` to apply the events to the TaskRecords in place, then builds the task table, the invalid list, `metrics.reviewer_table`, `metrics.annotator_table` and `reports.summarize`.

### 2. How does replay decide an event is invalid?

It looks up the task, the actor and the handler for the action. If any is missing, or the actor is inactive, the event id goes to `invalid`. Otherwise it calls the handler from `transitions.HANDLERS`; a False return also marks it invalid. Applied events are appended to `task.history` and to the `applied` list.

### 3. What is Event.seq and where is it set?

An integer parsed from the event id with the leading `E` stripped (`E12` becomes 12). It is set in `loader.load_events`, which also sorts the events before returning them.

### 4. Which attributes does TaskRecord set in __init__ and which come from the class?

Look at `models.TaskRecord`: the class body declares defaults for state, rework, assignee, submitter and closed_at (and any other class-level names), and `__init__` assigns task_id, queue, created_at plus whatever else it sets on `self`.

### 5. What does Member.can_review return?

It is a property that returns the result of an expression over `self.role`. `transitions._reviewable` wraps it in `bool()` and `metrics.reviewer_table` uses it to choose which members get a row.

### 6. How is the annotator `approved` count computed?

`annotator_table` walks the tasks and, for each task in the APPROVED state, adds one to the row of `task.submitter`, which `transitions.submit` sets to the actor of the last applied submit.

### 7. What are the units of cycle_hours?

It subtracts `created_at` from `closed_at` (both datetimes from parse_when) and divides a seconds value by 3600. `summarize` averages it over approved tasks and rounds to 2 decimals.
