# set-062 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside replay() for each request?

It calls `feed.apply_due(arrival)` to apply health transitions, `release_finished(workers, arrival)` to drop finished requests, then `pick_worker` on the workers of the request's zone. The chosen worker gets the request's end time appended to `inflight`; with no candidate the assignment is None. After the loop it calls `feed.flush()`.

### 2. What is stored in Worker.inflight?

A list of end times in ms, one per running request. `len(inflight)` is the number of running requests used by `has_room` and the score in `pick_worker`.

### 3. How does pick_worker break ties?

It takes `min` over eligible workers with the key `(len(inflight) / effective_weight(w), worker_id)`, so equal scores fall back to the worker id string.

### 4. What type is Worker.state after loading and after a health event?

`parse_state` returns a `WorkerState` member (a plain `Enum`, not a `str` subclass). Health events are parsed with the same function, and `apply_due` assigns `event.state` to the worker.

### 5. How does worker_stats work out peak_inflight?

For each worker it builds (arrival, end) intervals of its requests, turns them into (time, ±1) points with `sweep_points`, walks them in sorted order adding the deltas to `current`, and keeps the largest value seen in `peak`.

### 6. What does load_requests return, and in what order?

A list of `Request` objects sorted by `arrival_ms` with Python's stable sort, so same-time requests keep file order. A blank zone becomes `DEFAULT_ZONE` ("central").

### 7. When is out_of_rotation computed?

In `build_report`, after `replay` has returned. `replay` ends with `feed.flush()`, which applies any remaining health transitions, so it reads each worker's final state.
