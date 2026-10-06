# Load Balancer Replay

The `api` pool sits behind a software load balancer. To check a new configuration, this
tool replays a recorded request log, together with the health-check log from the same
window, through the balancer logic and reports where each request went.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: the `pool` to replay, and the health-check thresholds `fall` and `rise`.
- `data/backends.csv`: every backend in the cluster: `pool`, `zone`, `weight`, `max_conns`,
  `enabled` (`yes`/`y`/`true`/`1`, any case, means enabled; anything else, including
  blank, means disabled).
- `data/health.csv`: health-check results (`pass`/`fail`) over time.
- `data/requests.csv`: requests with their arrival time, session (may be blank) and
  `duration_ms`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Backend ids, pools, zones, sessions and check results: trim and lower-case.
  Request ids: trim and upper-case.
- Times (`t`) are offsets from the start of the recording: `1.5s`, `1500ms` or a bare
  number of milliseconds.

### Backends and health

1. Only enabled backends of the configured pool take part. Health checks for any other
   backend are ignored.
2. Every backend starts `healthy`. A healthy backend goes `down` after `fall`
   **consecutive** failed checks; any passing check resets that streak.
3. A down backend becomes `healthy` again after `rise` consecutive passing checks; a
   failed check resets that streak.
4. Before a request is routed, apply every health check with `t` ≤ the request's `t`.
   Requests are handled in time order (ties: request id).

### Routing

5. A request occupies its backend from `t` until `t + duration_ms`. At time `now`, a
   backend's active count is the number of its requests with an end time **after** `now`.
6. A backend is **usable** when it is healthy and its active count is below `max_conns`.
7. Sticky sessions: if the request has a session that was previously routed to a backend,
   and that backend is usable, the request goes there again.
8. Otherwise the request goes through smooth weighted round robin over the usable
   backends: add each usable backend's `weight` to its running score, pick the highest
   score (ties: lowest id), then subtract the sum of the usable weights from the winner.
   Scores of backends that were not usable are left alone, and a sticky reuse does not
   change any score.
9. If a session had a previous backend and is routed somewhere else, that is a
   **failover**. The session then sticks to the new backend.
10. If no backend is usable, the request is rejected (assigned `None`).

### Output

`lbreplay.report.build_report()` returns:

- `transitions`: `[t_ms, backend, new_state]` in the order they happened;
- `final_state`: state of each backend after the whole health log;
- `assignments`: request id → backend;
- `sessions`: session → the backend it ends up stuck to;
- `summary`:
  - `backends`: per backend, `requests` and `p50_ms`, the nearest-rank median of its
    requests' `duration_ms` (the ⌈n/2⌉-th smallest value);
  - `zones`: zone → number of requests routed to backends in that zone;
  - `failovers`: the number of failovers;
  - `rejected`: sorted ids of rejected requests.

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
