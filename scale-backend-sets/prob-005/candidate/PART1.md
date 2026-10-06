# Part 1: Correct delivery and an audit log (about 20 minutes)

Make `Dispatcher.dispatch_due()` deliver each event to each interested
subscriber correctly, remember what was delivered, and record every attempt.
State may live in memory for now (Part 3 makes it durable).

Keep the `Dispatcher(state_dir, events, subscriptions, http, clock, max_attempts=5, timeout_s=5.0)`
constructor and the `dispatch_due()` / `delivery()` methods. Use the injected
`http` client for every request and `clock.time()` for every timestamp.

## Deliveries

A **delivery** is one (event, subscription) pair. There is exactly one
delivery for every event in the events file and every subscription whose
`event_types` contains the event's `type` or `"*"`. Events with a type nobody
subscribed to (other than `"*"`) are simply not delivered.

Each delivery has a status: `pending` (not delivered yet), `delivered`, or
`dead` (given up; used from Part 2).

## `dispatch_due() -> DispatchReport`

Each call:

1. Re-reads the events file (so events appended since the last call are picked up).
2. Attempts every `pending` delivery once, in events-file order and, for each
   event, in subscriptions-file order. `delivered` deliveries are never sent again.

One **attempt** is one HTTP request:

* `POST` to the subscription's `url`.
* Body: the event as a JSON object with exactly the keys `id`, `type`,
  `created_at`, `data` (values as in the file).
* Headers:
  * `Content-Type: application/json`
  * `X-Event-Id: <event id>`
  * `X-Webhook-Signature: <sign(subscription.secret, body, int(clock.time()))>`, using
    `dispatcher/signing.py`. The signature must be computed over the **exact bytes
    sent** as the body; the receiver recomputes it and rejects mismatches.

Outcome of an attempt:

* a **2xx** response: the delivery becomes `delivered`;
* any other response, or any `httpx.HTTPError` raised by the client (e.g.
  `httpx.ConnectError`): the attempt **failed**. The delivery stays `pending` and
  is attempted again on the next `dispatch_due()` call. A failure never escapes
  `dispatch_due()` and never stops other deliveries from being attempted.

`DispatchReport` (already defined in `dispatcher/dispatcher.py`):

| field | meaning |
|---|---|
| `attempted` | number of attempts made in this call |
| `delivered` | attempts in this call that delivered |
| `failed` | attempts in this call that failed and left the delivery `pending` |
| `dead` | attempts in this call after which the delivery became `dead` (0 in Part 1) |
| `skipped_lines` | sorted 1-based line numbers of events-file lines that were skipped (see below) |

`attempted == delivered + failed + dead`.

## Bad lines in the events file

Blank (whitespace-only) lines are ignored and not reported. These lines are
**skipped** (no delivery is created) and their line numbers reported in
`skipped_lines`:

* not valid JSON, or not a JSON object;
* `id`, `type` or `created_at` missing or not a non-empty string, or `data` missing or not an object
  (the existing `Event.from_dict` already checks these);
* an `id` that already appeared on an earlier valid line (the first occurrence wins).

`skipped_lines` lists every skipped line in the file at the time of the call,
including ones reported by earlier calls.

## `delivery(event_id, subscription_id) -> dict`

```json
{"event_id": "evt_1", "subscription_id": "sub_a", "status": "pending",
 "attempts": 1, "next_attempt_at": 1700000000.0, "last_error": "HTTP 503"}
```

* `attempts`: attempts made so far for this delivery.
* `next_attempt_at`: unix seconds (float) when the delivery is next due, for a `pending`
  delivery (in Part 1: the time of its last failed attempt, i.e. due again right away);
  `null` once it is `delivered` or `dead`.
* `last_error`: `null` if the most recent attempt succeeded; otherwise a non-empty
  string describing it: `"HTTP <status>"` for a response (e.g. `"HTTP 503"`),
  `"<ExceptionClass>: <message>"` for an exception (e.g. `"ConnectError: connection reset"`).
* Raises `KeyError` if no such delivery exists (the event was not seen yet, or the
  subscription does not want its type).

## Audit log

Every attempt appends exactly one JSON line to `<state_dir>/audit.jsonl`, in the
order the attempts were made:

```json
{"ts": 1700000000.0, "event_id": "evt_1", "subscription_id": "sub_a", "attempt": 1,
 "outcome": "failed", "status_code": 503, "error": "HTTP 503"}
```

| key | value |
|---|---|
| `ts` | `clock.time()` when the attempt was made |
| `attempt` | 1-based attempt number of this delivery |
| `outcome` | `"delivered"`, `"failed"`, or `"dead"` (from Part 2: the attempt failed and the delivery is now dead) |
| `status_code` | the HTTP status as an int, or `null` if no response was received |
| `error` | `null` when delivered, otherwise the same string as `last_error` |

The file is append-only: never rewrite or truncate it.

## Constraints

* Write files only under `state_dir`.
* Write tests for your work (`tests/test_smoke.py` shows how to wire the mock receiver).
