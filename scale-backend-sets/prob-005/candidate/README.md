# Webhook dispatcher

Our platform records everything that happens (a task is completed, a batch is
exported, ...) as events in an append-only JSON Lines file. Customers register
webhook subscriptions, and a dispatcher process delivers matching events to
their URLs.

The dispatcher in this repo is a first cut: it works on a good day, but it
ignores responses, forgets everything between runs and re-sends every event
on every pass. You will make it production-ready in three parts. Your
interviewer gives you `PART1.md` first; the next part comes when you finish.

Read the existing code before you start. It is small.

## Layout

```
dispatcher/
  events.py          Event + EventStore: reads/appends the events file (JSON Lines)
  subscriptions.py   Subscription + load_subscriptions(): validated subscriptions file
  signing.py         sign(): the HMAC signature scheme subscribers verify
  dispatcher.py      Dispatcher + DispatchReport: the delivery loop (start here)
  __main__.py        the CLI
mock_services/
  webhooks.py        WebhookReceiver: an in-process subscriber with scripted failures
  webhook_server.py  the same receiver as a real local HTTP server
  clock.py           RealClock / FakeClock
data/
  events.jsonl       sample events, including broken lines
  subscriptions.json sample subscriptions
tests/               put your tests here
```

## Formats

`events.jsonl`, one event per line:

```json
{"id": "evt_0001", "type": "task.completed", "created_at": "2024-06-01T10:00:00Z", "data": {"task_id": "t_17"}}
```

`subscriptions.json`:

```json
[{"id": "sub_qa_bot", "url": "http://127.0.0.1:9100/hooks/qa-bot", "secret": "whsec_qa_bot_41d0",
  "event_types": ["task.completed", "task.failed"]}]
```

`"event_types": ["*"]` subscribes to every type.

## Setup and running

Python 3.10+ with `httpx pytest` (plus `fastapi uvicorn` for the optional local server).

```
python -m pytest                                      # run tests

# terminal 1: a local subscriber (answers 500 to the first 2 requests)
python -m mock_services.webhook_server --port 9100 --secret whsec_qa_bot_41d0 --fail-first 2
# terminal 2: one dispatch pass over the sample data
python -m dispatcher run --once --state-dir state \
    --events data/events.jsonl --subscriptions data/subscriptions.json
curl -s localhost:9100/_deliveries
```

The local server checks signatures with the one `--secret` you give it, so only
that subscription's deliveries show `"signature_valid": true`.

In tests, use `WebhookReceiver.transport()` with an `httpx.Client` and a
`FakeClock` instead of a server; see `tests/test_smoke.py`.

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.
