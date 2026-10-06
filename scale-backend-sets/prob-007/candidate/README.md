# pool: a job-processing worker pool

Our media pipeline turns uploads into thumbnails, transcodes and exports. The
jobs run on a fleet of worker nodes that crash, hang, get slow, restart and
join at any time. You will build the coordinator that owns the job queue and
keeps the fleet busy, in three parts. Your interviewer gives you `PART1.md`
first; the next part comes when you finish.

## Layout

```
pool/coordinator.py      Pool: the coordinator (start here; method stubs + the fixed constructor)
pool/demo.py             demo: runs data/jobs.jsonl through three local workers
mock_services/workers.py MockWorker / WorkerFleet / CrashingWorker: fake worker nodes and their errors
mock_services/clock.py   RealClock / FakeClock
data/jobs.jsonl          sample jobs, including malformed lines, duplicates and a poison job
tests/                   starter tests; add yours here
```

## Setup

Python 3.10+ with `pytest` (the mock workers also need `fastapi` and `httpx` installed).

```
python -m pytest      # run the tests
python -m pool.demo   # run the demo (works once Part 1 is done)
```

## Working with time

Everything time-related goes through the injected `clock` (`clock.time()`),
never the `time` module. The pool itself never sleeps. Tests use `FakeClock`:
`clock.advance(s)` / `clock.set(t)` move time, and a worker that "hangs for
2 seconds" returns instantly and simply moves the fake clock forward.
`WorkerFleet.run(seconds, sink=...)` advances the clock and delivers heartbeats.

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.
