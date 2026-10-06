# Part 3: Durability across restarts and crashes (about 20 minutes)

The dispatcher runs as a long-lived process that gets deployed, restarted and
occasionally killed. Today all delivery state is lost when it stops, so a
restart re-sends every event. Make the state durable.

## Requirements

1. **Persist delivery state under `state_dir`**, after every attempt and before the
   next attempt starts. The file layout is up to you (JSON files or sqlite), but a
   write must never leave a half-written or corrupt state behind: write a temp file
   and `os.replace` it over the old one, or use a sqlite transaction.

2. **Resume on restart.** A new `Dispatcher` constructed over the same `state_dir`
   (with the same events file and subscriptions) must, immediately and before any
   `dispatch_due()` call:
   * return the same `delivery(...)` dicts the previous instance would have returned
     after its last completed attempt (same `status`, `attempts`, `next_attempt_at`,
     `last_error`);

   and from then on:
   * never re-send a `delivered` delivery;
   * keep `dead` deliveries dead;
   * attempt `pending` deliveries on exactly their saved schedule;
   * pick up events appended to the events file since the last run.

3. **Idempotent re-runs.** Calling `dispatch_due()` again at the same clock time,
   on the same instance or on a new one, sends nothing new when nothing is due.

4. **The audit log keeps growing.** A new instance appends to the existing
   `<state_dir>/audit.jsonl`; earlier lines are never lost or rewritten.

5. **Crashes.** If the HTTP client raises an exception that is *not* an
   `httpx.HTTPError` (a bug, an out-of-memory error, the process being shut down),
   `dispatch_due()` must let it propagate. That attempt is not recorded. Every
   attempt completed before it stays saved.

## The guarantee

Deliveries are **at-least-once**: an event is never lost, but if the process dies
after a request was sent and before its result was saved, the restarted dispatcher
sends it again. Every attempt whose result was saved is never repeated.

## Discussion (no code required)

Be ready to talk about:

* at-least-once versus exactly-once: what subscribers must do with `X-Event-Id`,
  and whether exactly-once is achievable at all;
* one slow subscriber (every request takes the full 5 s timeout) holding up
  delivery to everyone else;
* 100x the event volume: what replaces "re-read the whole file and rewrite the whole
  state on every attempt", and what ordering guarantees subscribers can rely on.
