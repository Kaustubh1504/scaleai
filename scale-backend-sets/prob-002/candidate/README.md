# lb: in-process load balancer

`lb` routes tasks from our batch pipeline to a pool of worker nodes. It
started as a few lines of round robin; the pipeline team now needs it to cope
with workers that fill up, crash, hang, join and leave. You will extend it in
three parts. Your interviewer gives you `PART1.md` first; the next part comes
when you finish.

**Before writing code, spend a few minutes reading the existing package and
running its tests and demo.** Part of the exercise is working inside code you
did not write.

## Layout

```
lb/models.py            Task, DispatchResult, WorkerState, the Worker protocol
lb/registry.py          WorkerRegistry: the workers we know about, in registration order
lb/balancer.py          LoadBalancer: routing (start here) plus stubs for later work
lb/simulate.py          demo: dispatch data/tasks.jsonl across three local workers
mock_services/workers.py MockWorker / WorkerFleet: fake worker nodes and their errors
mock_services/clock.py  RealClock / FakeClock
data/tasks.jsonl        sample workload, including malformed lines
tests/                  existing tests; add yours here
```

## Setup

Python 3.10+ with `pytest` (the mock workers also need `fastapi` and `httpx` installed).

```
python -m pytest        # run the tests
python -m lb.simulate   # run the demo against data/tasks.jsonl
```

## Working with time

Everything time-related goes through the injected `clock` (`clock.time()`),
never the `time` module. Tests use `FakeClock`, so a worker that "hangs for
2 seconds" returns instantly and simply moves the fake clock forward.
`WorkerFleet.run(seconds, sink=...)` advances the clock and delivers heartbeats.

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.
