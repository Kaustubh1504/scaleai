# set-014 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What order does build_report run things in?

It loads workers (sorted by id), probes (sorted by time) and requests (sorted by arrival, blank durations skipped). `apply_probes` sets every worker's final state, `route` replays the requests against those states, and then the report is built from worker states, `availability`, the assignments, `peak_in_flight` and `zone_summary`.

### 2. How is a worker's initial state set?

In `loader.load_workers`, `admin` is trimmed and lower-cased; `draining` gives `State.DRAINING`, anything else `State.UP`. States are members of the `State` enum in models.py, whose values are the strings 'up', 'down' and 'draining'.

### 3. What does is_failure return?

True when the probe's (lower-cased) result is `fail` or `timeout`, False otherwise. It is defined in health.py and used by `apply_probes`.

### 4. How does the router track open connections?

Each Worker has an `active` list of connection end times. Before each request, `release_finished` keeps only end times later than the arrival time; routing appends `arrived_at + duration_ms` to the chosen worker and its request id to `worker.served`.

### 5. Which workers can pick_worker choose from?

Workers whose state is `State.UP` and whose `len(active)` is below `max_conns`. It uses the ones in the request's zone if there are any, otherwise all eligible workers, and takes the min of a key starting with `len(active) / weight`.

### 6. How does peak_in_flight work?

It builds a +1 event at arrival and a -1 event at arrival + duration for every routed request, sorts the events, and keeps a running sum, returning the maximum running value.

### 7. Where do the zone served counts come from?

`zone_summary` adds `len(worker.served)` for every worker into its zone. The mean durations come separately from the assignments dict and the requests' `duration_ms`.
