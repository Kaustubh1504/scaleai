# Part 2: Surviving a flaky, rate-limited API (about 20 minutes)

The export runs at night when the platform is under heavy batch load:
transient errors, hung requests, truncated bodies, and a strict rate limit.
One broken project must not stop the customer from getting the others.

## Transient failures

These are transient: any HTTP **5xx**, any `httpx.TransportError` (connection
errors and timeouts), and a 2xx whose body is not valid JSON.

* A request gets at most **5 attempts**.
* Before attempt `n + 1` (after the `n`-th transient failure), wait with
  `clock.sleep` for `2 ** (n - 1) + u` seconds, where `u` is drawn uniformly
  from `[0, 1]`. So the waits are about 1–2 s, 2–3 s, 4–5 s, 8–9 s.

## 429 Too Many Requests

* Wait the number of seconds in `Retry-After`, then send the same request again.
* If there is no `Retry-After`, wait until `X-RateLimit-Reset` (a Unix time:
  wait `reset - clock.time()` seconds). If neither header is there, wait 1 second.
* 429s do **not** count toward the 5 attempts. But **8** 429s in a row for the
  same request count as giving up on it (see below).

## Giving up on a project

When a request exhausts its attempts (or hits 8 consecutive 429s), that
project's entry becomes:

```json
{"status": "failed", "error": "<non-empty description>"}
```

with exactly those two keys. No file for it may remain in `out_dir` (remove the
partial one, and any left over from an earlier run). The export then **continues**
with the next project.

## Still fatal

`401` (`AuthError`) and other 4xx responses besides 404 are not retried. They
stop the export as in Part 1.

Write tests with scripted faults, e.g.
`make_api(faults=FaultConfig(scripted={"GET /v1/projects/prj_02/tasks?cursor": [503, "429:3"]}))`,
and assert on `clock.sleeps` and `api.log`.
