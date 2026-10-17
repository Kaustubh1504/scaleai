# State Machines and Leases in Python, Step by Step: Handing Out Work Without Losing or Duplicating It

### The pattern behind task queues, annotation tools, and seat holds

Any system that hands work to workers has the same problems. A worker takes a task and crashes. Two workers grab the same task. A "completed" task gets moved back to "pending" by a bug. A slow worker finishes *after* its task was given to someone else, and overwrites the newer result.

Two patterns fix all of these:

1. **A state machine** that only allows legal status changes.
2. **Leases**: time-limited claims on a task, with heartbeats and tokens.

**What you need:** Python 3.9+. Standard library only.

---

## Part 1: A state machine

### Step 1: Write the allowed transitions down as data

Statuses changed with scattered `if` statements drift over time. Put every legal move in one dictionary:

```python
TRANSITIONS = {
    "pending": {"leased", "cancelled"},
    "leased": {"pending", "completed", "failed"},
    "failed": {"pending", "dead"},
    "completed": set(),       # terminal
    "dead": set(),            # terminal
    "cancelled": set(),       # terminal
}
```

The whole lifecycle now fits on one screen, and an empty set marks a terminal state.

### Step 2: Reject illegal moves loudly

`completed → pending` should be an error, not something that silently happens. Raise a specific exception that your API maps to **409 Conflict**.

### Step 3: Make repeats harmless

Clients retry. If a task is already `completed` and the same "complete" request arrives again, that should succeed as a no-op, not fail with "invalid transition". Moving to the current state returns `False` and changes nothing.

### Step 4: Record every change

Pass a list (or a function that writes to your audit log), and append `{id, from, to, at}` for every real transition. When someone asks "why is this task dead?", you have the history.

### The complete snippet

```python
import time

TRANSITIONS = {
    "pending": {"leased", "cancelled"},
    "leased": {"pending", "completed", "failed"},
    "failed": {"pending", "dead"},
    "completed": set(),
    "dead": set(),
    "cancelled": set(),
}


class InvalidTransition(Exception):
    """Map to 409 Conflict."""


def transition(task: dict, to: str, transitions=TRANSITIONS, audit=None) -> bool:
    """Move task["status"] to `to`. Same state again -> no-op, returns False (safe to retry).
    Not allowed -> InvalidTransition. Appends {"id", "from", "to", "at"} to `audit` if given."""
    current = task["status"]
    if current == to:
        return False
    if to not in transitions.get(current, set()):
        raise InvalidTransition(f"{task.get('id')}: {current} -> {to} not allowed")
    task["status"] = to
    if audit is not None:
        audit.append({"id": task.get("id"), "from": current, "to": to, "at": time.time()})
    return True
```

```python
@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: str):
    task = tasks.get(task_id) or raise_404()
    try:
        changed = transition(task, "completed", audit=audit_events)
    except InvalidTransition as e:
        raise HTTPException(409, str(e))
    return {"task": task, "changed": changed}
```

---

## Part 2: Leases

### Step 5: Why a plain "assigned_to" field isn't enough

If you set `task["worker"] = "w1"` and w1 crashes, the task is stuck forever. A **lease** expires on its own: w1 owns the task for 30 seconds, and if it doesn't check in, the task becomes available again.

### Step 6: Heartbeats keep long work alive

Work that takes longer than the lease calls `heartbeat()` every `ttl / 3` seconds to extend it. If the worker dies, the heartbeats stop and the lease expires.

### Step 7: Tokens protect against stale workers

This is the subtle bug. w1's lease expires while it's merely slow, so the task goes to w2. Then w1 finishes and calls `complete()`. Without protection, w1's stale result overwrites w2's work.

The fix: every lease gets a fresh random **token**. Only the holder of the *current* token can heartbeat, complete or fail. w1's old token no longer matches, so its call returns `False`.

### Step 8: Count attempts, then give up

Every acquisition increments `attempts`. When a lease expires (or the worker calls `fail()`) on the last allowed attempt, the task becomes `dead` instead of `pending`. That's your dead-letter state: a task that keeps crashing workers stops being retried forever.

### Step 9: Expire lazily

You don't need a background timer. `acquire()` calls `reap_expired()` first, so expired leases are cleaned up whenever someone asks for work. For a status endpoint, call `reap_expired()` before reading.

### The complete snippet

```python
import time
import uuid


def new_item(item_id, payload=None) -> dict:
    return {"id": item_id, "payload": payload, "status": "pending", "attempts": 0,
            "worker": None, "token": None, "expires_at": 0.0}


def reap_expired(items: dict, max_attempts: int = 3, now=None) -> list:
    """Expired leases go back to pending, or to dead after max_attempts. Returns changed ids."""
    now = time.monotonic() if now is None else now
    changed = []
    for it in items.values():
        if it["status"] == "leased" and it["expires_at"] <= now:
            it["status"] = "dead" if it["attempts"] >= max_attempts else "pending"
            it["worker"] = it["token"] = None
            changed.append(it["id"])
    return changed


def acquire(items: dict, worker: str, ttl: float = 30.0, max_attempts: int = 3, now=None):
    """Lease the oldest pending item. Returns (item, token) or None. Hold a lock around calls if threaded."""
    now = time.monotonic() if now is None else now
    reap_expired(items, max_attempts, now)
    for it in items.values():
        if it["status"] == "pending":
            it.update(status="leased", worker=worker, token=uuid.uuid4().hex,
                      expires_at=now + ttl, attempts=it["attempts"] + 1)
            return it, it["token"]
    return None


def _holds(it, token, now) -> bool:
    return it is not None and it["status"] == "leased" and it["token"] == token and it["expires_at"] > now


def heartbeat(items: dict, item_id, token: str, ttl: float = 30.0, now=None) -> bool:
    """Extend the lease. False if the lease expired or someone else holds it now."""
    now = time.monotonic() if now is None else now
    it = items.get(item_id)
    if not _holds(it, token, now):
        return False
    it["expires_at"] = now + ttl
    return True


def complete(items: dict, item_id, token: str, result=None, now=None) -> bool:
    """Only the current holder can complete. Repeating the same completion returns True (idempotent)."""
    now = time.monotonic() if now is None else now
    it = items.get(item_id)
    if it is not None and it["status"] == "completed":
        return it.get("completed_token") == token
    if not _holds(it, token, now):
        return False
    it.update(status="completed", result=result, completed_token=token, token=None, worker=None)
    return True


def fail(items: dict, item_id, token: str, max_attempts: int = 3, now=None) -> bool:
    """Holder gives up: back to pending, or dead after max_attempts."""
    now = time.monotonic() if now is None else now
    it = items.get(item_id)
    if not _holds(it, token, now):
        return False
    it.update(status="dead" if it["attempts"] >= max_attempts else "pending", token=None, worker=None)
    return True
```

Every function takes an optional `now`, which makes the expiry logic testable without sleeping.

### Step 10: Use it from a worker loop

```python
import threading, time

lock = threading.Lock()
items = {t["id"]: new_item(t["id"], t) for t in tasks}

def worker(name):
    while True:
        with lock:
            lease = acquire(items, name, ttl=30)
        if lease is None:
            return
        item, token = lease
        try:
            result = process(item["payload"])          # call heartbeat() inside long work
            with lock:
                complete(items, item["id"], token, result=result)
        except Exception:
            with lock:
                fail(items, item["id"], token)
```

The functions change shared dictionaries, so wrap each call in one lock when several threads use them. In a database, the same logic becomes one conditional `UPDATE ... WHERE id = ? AND token = ? AND expires_at > now`.

---

## Testing with a fake clock

```python
def test_lease_lifecycle():
    items = {i: new_item(i) for i in ["a", "b"]}
    item, tok = acquire(items, "w1", ttl=10, now=0)
    assert heartbeat(items, "a", tok, ttl=10, now=5)            # extends to 15
    assert acquire(items, "w2", ttl=10, now=20)[0]["id"] == "a" # expired -> re-leased
    assert not complete(items, "a", tok, now=21)                # stale worker rejected


def test_gives_up_after_max_attempts():
    items = {"x": new_item("x")}
    for t in range(3):
        acquire(items, "w", ttl=1, max_attempts=3, now=t * 10)
    reap_expired(items, max_attempts=3, now=100)
    assert items["x"]["status"] == "dead"
```

---

## Recap

1. Keep **legal transitions in one table.** Raise (409) on illegal moves, and treat repeats as no-ops.
2. **Audit every transition.**
3. Use **leases with expiry** instead of permanent assignment.
4. **Heartbeat** during long work.
5. Give **every lease a new token**, so stale workers can't overwrite newer work.
6. **Count attempts** and move repeat offenders to `dead`.
