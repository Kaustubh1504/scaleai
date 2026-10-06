# Pool Balancer Replay

A replay tool for the inference load balancer. It rebuilds each backend worker's health
from the probe log, then replays a burst of requests through the routing policy and
reports where every request went and how busy each zone was.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/workers.json`: the pool: `id`, `zone`, `weight`, `max_conns`, `admin`
  (`active` or `draining`).
- `data/probes.csv`: health checks: `worker_id`, `checked_at`, `result`
  (`ok`, `fail` or `timeout`), `latency_ms` (blank when the check failed).
- `data/requests.csv`: `request_id`, `zone`, `arrived_at`, `duration_ms`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Worker and request ids: trim and upper-case (`w-02` → `W-02`). Zones and probe
  results: trim and lower-case. `admin` is compared after trimming and lower-casing.
- Timestamps use one of `2026-06-01 10:00:00`, `06/01/2026 10:00:00` (month/day/year)
  or `2026-06-01T10:00:00`.
- Requests with a blank `duration_ms` are not routed.

### Health

1. Every worker starts `up`, except `admin: draining` workers, which start `draining`.
2. Replay the probes oldest first. `fail` and `timeout` both count as failures.
3. A worker that is not `down` goes `down` after 3 failures in a row. A `down` worker
   goes back `up` after 2 passing probes in a row. A passing probe resets the failure
   streak and a failure resets the passing streak.
4. A `draining` worker ignores probes completely and stays `draining`.
5. `availability` = passing probes ÷ all probes for that worker in the last five minutes
   of the log: `checked_at` strictly after (latest `checked_at` in the file − 5 minutes).
   A worker with no probes in that window gets `None`. Rounded to 3 decimals.

### Routing

Health is evaluated over the whole probe log first; requests are then replayed against
the resulting states, in arrival order (file order for equal times).

6. Only `up` workers with fewer open connections than `max_conns` are eligible.
   A connection is open from `arrived_at` until `arrived_at + duration_ms`; one that ends
   exactly when a request arrives is already closed for that request.
7. Prefer eligible workers in the request's zone. If there are none, use every eligible
   worker.
8. Pick the worker with the lowest `open connections ÷ weight`. A **higher weight means
   the worker should take more traffic**, so on a tie the higher weight wins; after that
   the lower worker id.
9. A request with no eligible worker at all is rejected.

### Report

`lbsim.reports.build_report()` returns:

- `workers`: worker id → final state (`up`, `down`, `draining`);
- `availability`: worker id → availability;
- `assignments`: request id → worker id; `rejected`: rejected request ids in arrival order;
- `peak_in_flight`: the largest number of routed requests open at the same moment
  (a request ending at the instant another starts does not overlap it);
- `zones`: for each zone of the pool (sorted), `served` (requests routed to workers in
  that zone) and `mean_duration_ms` (mean `duration_ms` of those requests, rounded to
  1 decimal, `None` if there are none).

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
