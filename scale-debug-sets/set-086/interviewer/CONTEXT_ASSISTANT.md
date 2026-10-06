# set-086 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. In what order does Replay.run process health checks and requests?

Checks and requests are each sorted by time. Before routing a request, every check with t_ms <= the request time is fed to `HealthTracker.observe`. After the last request, the remaining checks are applied, so `final_state` reflects the whole health log.

### 2. What does HealthTracker ignore?

Checks for backend ids that are not in its `state` dict. The tracker is built from the loaded backends, i.e. enabled `api` backends only.

### 3. How does route() decide where a request goes?

It looks up the session's previous backend. If there is one and the state check and `has_room` both pass, it reuses it. Otherwise it builds the eligible list with `usable()` (healthy and below max_conns), calls `rr.pick`, and counts a failover when the session had a previous backend and the new pick differs. The chosen backend gets the request's end time in `inflight` and becomes the session's sticky backend.

### 4. How is a backend's in-flight count computed?

`active(bid, now)` keeps only end times strictly greater than `now` and returns how many are left. A request that ends exactly at `now` no longer counts.

### 5. What does the SWRR `current` dict look like over time?

It starts at 0 for every loaded backend. Each pick adds each eligible backend's weight to its value and subtracts the eligible total from the winner. Backends that were not eligible for a pick are left unchanged. A sticky reuse does not touch `current`.

### 6. How are request times parsed?

`parse_offset` accepts `1.5s`, `1500ms` or a bare `1500` (milliseconds) and returns integer milliseconds. Request ids are upper-cased and sessions lower-cased. A blank session means no stickiness.

### 7. What goes into summary.backends?

`per_backend` groups each routed request's duration_ms by its assigned backend and returns `requests` (the count) and `p50_ms` from `p50()` for every loaded backend, sorted by id.
