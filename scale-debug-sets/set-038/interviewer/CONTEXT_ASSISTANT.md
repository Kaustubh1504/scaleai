# set-038 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does simulate.run do for each request?

In arrival order it calls release_finished, advances the ProbeFeed to the request's arrival time, builds the candidate list for the request's pool, and calls pick with the client's sticky backend id for that pool. The chosen backend gets the connection via assign() and becomes sticky; if pick returns None the route is None.

### 2. How are open connections stored?

Each Backend has `active`, a list of connection end times in ms. assign() appends arrival + duration and updates served, busy_ms and peak; release_finished filters the list against the current time.

### 3. How does a probe change a backend?

health.apply_probe: a healthy probe sets healthy True; a failed one increments backend.fails and marks the backend unhealthy once fails reaches FAILS_TO_DOWN (2). ProbeFeed.advance applies probes in time order up to the current time.

### 4. What does parse_ms accept?

Plain integers ('1200'), an 'ms' suffix, or an 's' suffix with a decimal ('1.65s' -> 1650). Blank or missing text returns the `default` argument (None unless given).

### 5. Where does the request order come from?

load_requests sorts the parsed rows by arrival_ms with Python's stable sort, so equal arrivals keep their file order (R15 before R16 at 2000, R24 before R25 at 3200).

### 6. How is utilization computed?

reports.summarize takes window = latest connection end minus earliest arrival (4100 ms with this data) and, for each backend with served > 0, busy_ms / (window * max_conns), rounded to 3 decimals.
