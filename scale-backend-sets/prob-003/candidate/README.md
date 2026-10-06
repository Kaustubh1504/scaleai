# Task intake service

Customers (tenants) push annotation tasks into our platform through an intake
API. Their clients retry on network errors, tenants on different plans get
different throughput, and the service is restarted on every deploy. You will
build the service in three parts. Your interviewer gives you `PART1.md` first;
the next part comes when you finish.

## Layout

```
app/main.py              create_app(): the FastAPI app (start here)
mock_services/clock.py   RealClock / FakeClock
data/tenants.json        plans and tenants (the default config)
data/sample_requests.jsonl  example requests, including malformed bodies, for manual testing
tests/                   put your tests here
```

## Tenant config

`create_app(tenants=...)` takes one dict with two keys (the default is
`data/tenants.json`):

```json
{
  "plans":   {"free": {"burst": 5, "refill_per_s": 1.0}, "pro": {"burst": 20, "refill_per_s": 10.0}},
  "tenants": {"acme": {"plan": "pro"}, "globex": {"plan": "free"}}
}
```

Every tenant's `plan` names a key of `plans`. Tests may use other plan names
and numbers.

## Setup

Python 3.10+ with `fastapi uvicorn httpx pydantic pytest`.

```
python -m pytest              # run tests
uvicorn app.main:app --reload # run the service on :8000
curl -i -X POST localhost:8000/tasks -H 'X-Tenant-Id: acme' -H 'Idempotency-Key: order-1001' \
     -H 'Content-Type: application/json' -d '{"project": "lidar-3d", "payload": {"scene": "s-002"}}'
```

Each line of `data/sample_requests.jsonl` has `tenant` (the `X-Tenant-Id`
header, `null` = omit it), `key` (the `Idempotency-Key` header, `null` = omit
it) and `body` (the raw request body, as a string).

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.
