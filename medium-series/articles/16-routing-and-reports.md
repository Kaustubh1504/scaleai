# Load Balancers, Worker Pools, and Reports in Python, Step by Step

### Route work to healthy workers, detect silent ones with heartbeats, and compute report numbers correctly

Two kinds of problem show up constantly in backend work:

- **Routing:** send each task to a worker that's up and not overloaded, fail over when one breaks, and notice workers that went quiet.
- **Reporting:** medians, completion rates and per-customer rollups that are correct at the edges: no tasks, missing values, ties.

We'll build two standalone snippets: `worker_routing` and `stats_helpers`.

**What you need:** Python 3.9+. Standard library only.

---

## Part 1: Routing and health

### Step 1: Store workers as plain records

```python
workers = {"w1": new_worker("w1", seq=0, now=clock.time()), ...}
```

Each record has a registration `seq` (for ordering), a `state` (`active`, `overloaded` or `unreachable`), `last_seen`, the reported load, and an overload cooldown.

### Step 2: Round robin that survives removals

"Start at the worker after the one tried last, wrap around, try each worker once." The naive version stores an *index*, which breaks as soon as a worker is removed and everything shifts. Store the last tried worker's **`seq`** instead. The next pass starts with the first worker whose `seq` is higher, then wraps. That still works if the last tried worker no longer exists.

### Step 3: Least loaded, with a deterministic tie-break

To balance by load instead, pick the eligible worker with the smallest load, and break ties by registration order, so the result never depends on how a dict happens to be ordered.

### Step 4: Heartbeats use *your* clock

Validate every heartbeat: it must be a dict, `worker_id` a string, and `in_flight`/`capacity` real integers (`True` is an `int` in Python, so exclude booleans). Ignore malformed heartbeats and unknown workers silently. Record `last_seen = now` from **your** clock, never the payload's `ts`: worker clocks can be wrong.

### Step 5: Load decides state, and cooldowns expire lazily

`in_flight >= capacity` means `overloaded` until `now + cooldown`. A lower-load heartbeat brings the worker back right away. `state_at()` checks the cooldown whenever you look at the worker, so no background timer is needed.

### Step 6: Health checks only demote

`check_health()` marks workers silent for **more than** the timeout as `unreachable` (exactly at the timeout is still fine). It never revives anyone. Only a real heartbeat does that, because a worker that's silent is not proof that it's back.

### The complete snippet

```python
def new_worker(worker_id: str, seq: int, now: float) -> dict:
    return {"id": worker_id, "seq": seq, "state": "active", "last_seen": now,
            "in_flight": 0, "capacity": 1, "cooldown_until": None}


def rotation(workers: list, last_seq=None) -> list:
    """One round-robin pass: workers registered after the last one tried, then wrap around.
    `workers` is in registration order with increasing "seq". Works if the last tried worker was removed."""
    if last_seq is None:
        return list(workers)
    return [w for w in workers if w["seq"] > last_seq] + [w for w in workers if w["seq"] <= last_seq]


def least_loaded(workers: list, load, eligible=lambda w: True):
    """Eligible worker with the lowest load(w); ties go to the earliest in the list. None if none eligible."""
    best = None
    for w in workers:
        if eligible(w) and (best is None or load(w) < load(best)):
            best = w
    return best


def state_at(worker: dict, now: float) -> str:
    """Overloaded workers become active again once their cooldown has passed."""
    if worker["state"] == "overloaded" and worker["cooldown_until"] is not None and now >= worker["cooldown_until"]:
        worker.update(state="active", cooldown_until=None)
    return worker["state"]


def on_heartbeat(workers: dict, payload, now: float, cooldown: float = 5.0) -> bool:
    """Apply a heartbeat {"worker_id", "in_flight", "capacity", ...}. Ignores malformed payloads and unknown ids.
    Uses OUR clock (now), never payload["ts"]. Load decides state, even for an unreachable worker."""
    def is_int(v):
        return isinstance(v, int) and not isinstance(v, bool)

    if not (isinstance(payload, dict) and isinstance(payload.get("worker_id"), str)
            and is_int(payload.get("in_flight")) and is_int(payload.get("capacity"))
            and payload["in_flight"] >= 0 and payload["capacity"] >= 1):
        return False
    w = workers.get(payload["worker_id"])
    if w is None:
        return False
    w.update(last_seen=now, in_flight=payload["in_flight"], capacity=payload["capacity"])
    if payload["in_flight"] >= payload["capacity"]:
        w.update(state="overloaded", cooldown_until=now + cooldown)
    else:
        w.update(state="active", cooldown_until=None)
    return True


def check_health(workers: dict, now: float, timeout: float) -> list:
    """Silent for MORE than `timeout` seconds -> unreachable. Never revives a worker (only heartbeats do)."""
    changed = []
    for wid, w in workers.items():
        if now - w["last_seen"] > timeout and w["state"] != "unreachable":
            w["state"] = "unreachable"
            changed.append(wid)
    return changed
```

### Step 7: Dispatch with failover

```python
def dispatch(task, workers, state, now):
    for w in rotation(list(workers.values()), state.get("last_seq")):
        if state_at(w, now) != "active":
            continue
        state["last_seq"] = w["seq"]                     # "tried" counts whatever the outcome
        task["attempts"] += 1
        try:
            return w["client"].process(task["payload"], timeout=2.0)
        except OverloadedError:
            w.update(state="overloaded", cooldown_until=now + 5.0)
        except (UnreachableError, TimeoutError):
            w["state"] = "unreachable"
    raise NoWorkersAvailable(task["id"])
```

For a priority queue with retry budgets on top of this, see part 11 (the `priority_queue` and `retry_pool` snippets).

---

## Part 2: Report math that's right at the edges

### Step 8: A missing median is `None`, not 0

A project with no completed tasks has no median. Returning 0 makes it look like tasks finished instantly. Skip `None` values, and return `None` when nothing is left.

### Step 9: Rates handle a zero denominator

`completion_rate = completed / total` divides by zero for an empty project. Decide what the spec wants (0.0 or `None`), make it a parameter, and round as the spec says (4 decimal places is common).

### Step 10: Roll up sums, then compute rates

The classic mistake: a customer's completion rate computed by *averaging* its projects' rates. A 1-task project then counts as much as a 1,000-task project. Sum the counts per customer, **then** divide.

### The complete snippet

```python
import math
import statistics


def median(values):
    """Median ignoring None; None for no values (not 0, which would look like real data)."""
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def rate(part, whole, ndigits: int = 4, empty=0.0):
    """part / whole rounded; `empty` when whole is 0 (decide: 0.0 or None)."""
    return round(part / whole, ndigits) if whole else empty


def percentile(values, p: float):
    """Nearest-rank percentile, p in [0, 100]. None for no values."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    return vals[max(1, math.ceil(p / 100 * len(vals))) - 1]


def rollup(rows, key, fields) -> list:
    """Sum `fields` per key(row): [{"key": k, "count": n, field: total, ...}] sorted by key."""
    out = {}
    for r in rows:
        k = key(r)
        agg = out.setdefault(k, {"key": k, "count": 0, **{f: 0 for f in fields}})
        agg["count"] += 1
        for f in fields:
            agg[f] += r.get(f) or 0
    return [out[k] for k in sorted(out)]
```

```python
for c in rollup(projects, key=lambda p: p["customer_id"], fields=["tasks_total", "tasks_completed"]):
    c["completion_rate"] = rate(c["tasks_completed"], c["tasks_total"])
```

`rollup` returns rows sorted by key, so the report order is deterministic.

---

## Testing

```python
def test_rotation_survives_removal():
    ws = {w: new_worker(w, i, 0) for i, w in enumerate(["w1", "w2", "w3"])}
    assert [w["id"] for w in rotation(list(ws.values()), last_seq=0)] == ["w2", "w3", "w1"]
    del ws["w2"]
    assert [w["id"] for w in rotation(list(ws.values()), last_seq=1)] == ["w3", "w1"]


def test_heartbeats_and_health():
    ws = {"w1": new_worker("w1", 0, 0), "w3": new_worker("w3", 1, 0)}
    assert not on_heartbeat(ws, {"worker_id": "w1", "in_flight": True, "capacity": 2}, now=1)  # bool rejected
    on_heartbeat(ws, {"worker_id": "w1", "in_flight": 2, "capacity": 2}, now=10, cooldown=5)
    assert state_at(ws["w1"], 14) == "overloaded" and state_at(ws["w1"], 15) == "active"
    assert check_health(ws, now=13, timeout=3) == ["w3"]       # w1 seen at 10: exactly 3 s is fine


def test_rates_from_sums():
    rows = [{"c": "a", "done": 1, "total": 1}, {"c": "a", "done": 0, "total": 99}]
    (agg,) = rollup(rows, lambda r: r["c"], ["done", "total"])
    assert rate(agg["done"], agg["total"]) == 0.01            # not the 0.5 that averaging gives
```

---

## Recap

1. **Round robin by registration `seq`,** not by index, so it survives removals.
2. **Least loaded,** with ties broken by registration order.
3. **Heartbeats:** validate strictly (no booleans as integers), use your own clock, and let load decide the state.
4. **Health checks only demote,** and only *strictly* after the timeout.
5. **Reports:** a missing median is `None`, rates handle a zero total, and rates come from summed counts.
