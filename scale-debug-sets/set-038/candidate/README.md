# Load Balancer Replay

Replays a recorded request log through a weighted least-connections load balancer, so we
can see where each request would have gone. Backends are grouped into pools, have a
connection cap, can be disabled, and are taken out of rotation by health probes. Clients
stick to the backend that last served them in a pool while it is available.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/backends.json`: `id`, `pool`, `weight`, `max_conns`, `enabled`.
- `data/requests.csv`: `request_id`, `pool`, `client_id`, `arrival`, `duration`.
- `data/health.csv`: probe results: `backend_id`, `at`, `healthy`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Backend ids, pool names and client ids: trim, lower-case. Request ids: trim, upper-case.
- Times (`arrival`, `duration`, `at`) are milliseconds, written `1200`, `1200ms` or `1.2s`.
  A blank `duration` means 100 ms. A duration of `0` is a real zero-length request.
- `enabled` and `healthy` are JSON booleans/numbers or strings. As strings, `true`, `yes`,
  `y`, `1`, `up` and `ok` (any case) mean true and anything else means false. A missing
  `enabled` means enabled.

### Health

- Every backend starts healthy.
- A backend goes **down** after 2 consecutive failed probes. One healthy probe brings it
  back up and resets the count, so fail / ok / fail does not take it down.

### Routing

Requests are handled in `arrival` order (ties keep file order). For each request at time `t`:

1. Close every connection whose end time (`arrival + duration`) is ≤ `t`.
2. Apply every probe with `at` ≤ `t`, in time order.
3. Candidates: backends in the request's pool that are enabled, healthy and have fewer
   than `max_conns` open connections.
4. If the client's sticky backend for this pool is a candidate, use it.
5. Otherwise pick the candidate with the lowest load, where load = open connections ÷
   `weight` (a real ratio, so 1 connection on weight 2 is 0.5). Ties: the **higher**
   weight wins, then the alphabetically first id.
6. No candidate → the request is rejected (route `None`).
7. The chosen backend becomes the client's sticky backend for the pool.

### Report

`lbsim.reports.build_report()` returns:

- `routes`: `{request_id: backend_id or None}`;
- `backends`: per backend `served` (requests routed to it), `peak` (most open connections
  at once) and `busy_ms` (sum of durations served);
- `summary`:
  - `routed`, `rejected`, and `reject_rate` = rejected ÷ all requests (3 decimals);
  - `by_pool`: number of **routed** requests per pool;
  - `utilization`: for each backend that served anything, `busy_ms ÷ (window × max_conns)`,
    3 decimals, where `window` runs from the first arrival to the last connection end.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
