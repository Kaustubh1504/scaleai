# Part 3: Many annotators at once (about 20 minutes)

The service is about to be opened to a much larger annotator pool. At shift
start hundreds of annotators press "next task" within the same second, and we
deploy several times a day.

## 1. Atomic claims

Concurrent requests must never break the Part 1 and Part 2 rules. In
particular, with `N` requests arriving at the same moment from different
threads:

* no task ever has more live leases + submissions than `redundancy`;
* no annotator ever gets two different tasks, or two leases on the same task
  (concurrent claims by the same annotator all return the same task);
* concurrent submissions that complete a task produce exactly one final state
  computed from all `redundancy` submissions;
* no request fails with a 500 (for example `database is locked`) under this load.

The tests fire 20 threads at the service at once (`TestClient` from several
threads, so sync endpoints really run in parallel).

## 2. Restarts

A process restart must lose nothing. A new `create_app(...)` over the same
`storage_dir` (and the same clock) must see every task, live lease and
submission made through the old one: a lease taken before the restart still
blocks other annotators until it expires, its holder can still extend and
submit it, and consensus results are unchanged.

## 3. Discussion (no code required)

Be ready to talk about:

* choosing `lease_seconds` when some tasks take 20 seconds and some take 20
  minutes (heartbeats / extend, what happens to an annotator whose lease
  expired mid-task);
* this service and the annotator UI running on machines whose clocks disagree
  by a few seconds;
* serving `POST /tasks/claim` at 1,000 requests per second: what breaks first,
  and how you would claim fairly without every request contending for the
  same "oldest" row.
