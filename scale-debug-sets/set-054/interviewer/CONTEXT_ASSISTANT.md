# set-054 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. How does build_report run the replay?

It loads tasks.csv into Task objects, builds a ReviewMachine, calls `machine.handle(event)` for every event in file order, and then builds each report section from the machine's tasks (sorted by task number), `accepted` events and `rejected` (event, reason) pairs.

### 2. What does ReviewMachine.apply do with an event?

It looks up the task (UnknownTask if missing), finds a method named `_<action>` (InvalidTransition if there is none), calls it, and appends the event to `accepted` if nothing raised. handle() wraps apply() and maps the raised exception class to a reason string.

### 3. What exception classes exist and how are they related?

In models.py: ReviewError is the base; UnknownTask, InvalidTransition and AssignmentError subclass it; ConflictOfInterest subclasses AssignmentError.

### 4. Where is a task's history recorded?

Task.__init__ starts it with State.SUBMITTED, and Task.move appends each new state (and also sets state, entered_at, and decided_at for approved/rejected). The report converts each entry with `.value`.

### 5. Which timestamp does the waiting queue use?

`entered_at`, which Task.move updates on every transition. A resubmitted task's entered_at is therefore its resubmit time, not its original submitted_at.

### 6. How are reviewer stats counted?

reviewer_stats walks the accepted events: a `claim` makes sure the actor has an entry, and pass/request_changes/reject increment passed/changes/rejected for that actor. Resubmits aren't counted.

### 7. What does cycle_hours measure?

For tasks whose state is in DECIDED, the difference decided_at − submitted_at (both datetimes) converted to hours and rounded to 1 decimal.
