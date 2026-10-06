# Relay Mesh Replay

Relay Mesh is the router in front of our inference workers. To tune it we replay a
ten-second slice of production traffic (12:00:00 to 12:00:10) against a snapshot of the
worker pool, together with the health-check transitions that happened in that slice.
This repo runs that replay and reports where every request went, how loaded each worker
was, and which requests had nowhere to go.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/workers.json`: the pool snapshot (`id`, `zone`, `weight`, `max_inflight`,
  `state`).
- `data/requests.csv`: the traffic (`request_id`, `zone`, `arrived_at`, `duration`).
- `data/health.csv`: health-check transitions (`at`, `worker_id`, `state`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Request ids, worker ids and zones: trim and lower-case (`East-2 ` → `east-2`). A blank
  request zone means `central`.
- `weight` may be a number or a numeric string. A **missing** `max_inflight` means `2`;
  an explicit `0` means the worker is still provisioning and can take nothing.
- A missing `state` means `healthy`. States are `healthy`, `degraded`, `draining` and
  `down` (any case, stray spaces allowed).
- Times are `12:00:03` or `12:00:03.250`, measured in ms from 12:00:00. Durations are
  `850ms`, `1.2s` or a bare number of milliseconds.
- Requests are replayed in arrival order. Requests with the same arrival time keep their
  file order.

### Routing (for each request, in order)

1. Apply every health transition whose time is at or before the request's arrival.
   Transitions for unknown workers are ignored.
2. A running request occupies its worker from `arrival` up to `arrival + duration`.
   A request whose end time is at or before the new arrival has finished and no longer
   counts.
3. Candidates are the workers **in the request's zone** that are `healthy` or `degraded`
   and have fewer running requests than `max_inflight`. Requests never leave their zone.
4. Pick the candidate with the lowest `running ÷ effective weight`. Effective weight is
   `weight`, halved for a `degraded` worker. Ties go to the lowest worker id.
5. With no candidate the request is **rejected** (its assignment is `null`).

### Report

`relaymesh.report.build_report()` returns:

- `assignments`: request id → worker id, or `None` when rejected.
- `workers`: for every worker, sorted by id:
  - `served`: requests assigned to it;
  - `busy_s`: total duration of those requests in seconds, rounded to 2 decimals;
  - `utilisation_pct`: total duration as a percentage of the 10 s window, rounded to
    1 decimal (it can exceed 100 for a worker that runs requests in parallel);
  - `peak_inflight`: the most requests it was running at the same moment, counting a
    request that ends exactly when another starts as already finished.
- `summary`:
  - `requests_by_zone`: zone → number of requests;
  - `rejected`: sorted ids of rejected requests;
  - `out_of_rotation`: sorted ids of workers whose state is `down` or `draining` after
    every transition in `health.csv` has been applied.

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
