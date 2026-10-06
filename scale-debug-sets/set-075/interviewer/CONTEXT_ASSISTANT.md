# set-075 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does replay() do with each event?

If the event is the first one after the checkpoint, it reaps at checkpoint_ms and stores snapshot(broker.tasks). Then it reaps at the event time and calls poll/heartbeat/ack/fail on the Broker. Any LeaseError is converted with rejection_code() and counted in a Counter.

### 2. How does the Broker decide who owns a task in _owned()?

Unknown task id raises LeaseError. If task.owner equals the worker the task is returned. If the worker is in task.past_owners it raises LeaseExpired, otherwise NotOwner.

### 3. What happens in _release()?

It drops the worker from holding, appends the owner to past_owners, clears owner and expires_ms, and sets state to 'dead' if attempts >= max_attempts, else 'ready'. Both reap() and fail() use it.

### 4. How are the exception classes related?

LeaseExpired and NotOwner are both subclasses of LeaseError, defined in models.py.

### 5. What units are times stored in?

Everything is epoch milliseconds: loader.to_epoch_ms converts enqueued_at and the checkpoint, events carry at_ms, and lease_ms is lease_seconds * 1000.

### 6. Where is the checkpoint view built?

replay() returns the checkpoint mapping from snapshot(); build_report passes it to task_view(), the same function used for the final view.

### 7. Which events are dropped before replay?

load_events skips rows whose normalised worker id is not in the active set from load_workers, then sorts the rest by at_ms (a stable sort, so ties keep file order).
