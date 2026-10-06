# Part 3: Restarts, concurrent retries, expiry (about 20 minutes)

The service is redeployed several times a day, and clients fire retries in
parallel. Harden the intake.

## 1. Durability

Persist tasks and idempotency records under `storage_dir` (JSON files or
sqlite: your choice). A **new** `create_app(...)` over the same `storage_dir`
(simulating a restart) must:

* serve `GET /tasks/{task_id}` and `GET /tasks` (same order) exactly as before;
* replay an idempotent request exactly as before (same status, same JSON body,
  `Idempotent-Replayed: true`), and answer a different body with that key with 409.

A crash must never leave a half-written file that breaks the next start
(write atomically). Rate-limit buckets do not need to survive a restart.
An app over a different `storage_dir` must not see these tasks.

## 2. Concurrent identical requests

Clients sometimes send the same request from several threads at once. For N
concurrent `POST /tasks` with the same tenant, same `Idempotency-Key` and same
body:

* exactly **one** task is created;
* every response is either a **201** whose body is that task, or a **409**
  (with a `detail` such as "a request with this key is in progress");
* exactly one of the 201s is the original (no `Idempotent-Replayed` header);
  any other 201 is a replay with `Idempotent-Replayed: true`.

Tests send these from several OS threads, each with its own `TestClient` over
the same app, so your handlers can run in several threads (and event loops)
at the same time.

Concurrent requests with **different** keys must all be handled correctly, and
the rate limit must hold under concurrency (a tenant with `burst` 5 that sends
10 concurrent creations at the same clock time gets exactly 5 201s and 5 429s).

## 3. Expiry

An idempotency record expires **24 hours** (86 400 s of `clock.time()`) after
the task was created: a record created at time `t` is honoured while
`clock.time() < t + 86400`. From then on the key is unused again: a request
with that key (any body) creates a new task and becomes the new record. The
old task itself stays readable.

## 4. Discussion (no code required)

Be ready to talk about:

* enforcing per-tenant rate limits when the API runs as 30 instances behind a
  load balancer;
* storing idempotency records at scale: TTLs, key cardinality, what exactly to
  store, where;
* what happens if the process crashes after creating the task but before
  saving the idempotency record, and how you would design that away.
