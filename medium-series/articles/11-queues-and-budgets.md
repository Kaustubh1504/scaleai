# Job Queues in Python, Step by Step: Priorities, Retries, Dead Letters, and LLM Budgets

### Three snippets for running lots of work without losing control of order, failures, or cost

Once a backend processes more than a handful of jobs, three questions come up:

- **Which job runs next,** and what if its priority changes while it waits?
- **What happens when a job keeps failing?**
- **How do we stop an LLM batch from spending $500 overnight?**

We'll build three standalone snippets: a priority queue with updates, a retrying worker pool with a dead-letter list, and a token budget.

**What you need:** Python 3.9+. Standard library only.

---

## Part 1: A priority queue you can update

### Step 1: `heapq` gives you the minimum fast

`heapq.heappush` and `heapq.heappop` give you the smallest item in O(log n). Push `(deadline, task_id)` tuples, and the earliest deadline pops first.

### Step 2: Make ties first-in, first-out

With equal deadlines, tuples fall back to comparing `task_id`, which isn't arrival order. And if your payload is a dict, comparing two dicts raises a `TypeError`. Add an increasing sequence number as the second element: `(deadline, seq, task_id)`. Ties now pop in arrival order, and payloads are never compared.

### Step 3: Updating a priority, without searching the heap

Finding an entry inside a heap is O(n). Instead, use **lazy deletion**:

- Keep a `live` dict mapping `id → (priority, seq, payload)`.
- To update, push a *new* heap entry with a new `seq`, and overwrite `live[id]`.
- When popping, skip any heap entry whose `seq` no longer matches `live[id]`. It's stale.

Removing an item works the same way: delete it from `live`, and its heap entry is skipped later.

### The complete snippet

```python
import heapq
import itertools


def pq_new() -> dict:
    return {"heap": [], "live": {}, "seq": itertools.count()}


def pq_push(pq: dict, item_id, priority, payload=None) -> None:
    """Add, or change the priority of an existing id. Lower priority value pops first; ties pop FIFO."""
    seq = next(pq["seq"])
    pq["live"][item_id] = (priority, seq, payload)
    heapq.heappush(pq["heap"], (priority, seq, item_id))


def pq_remove(pq: dict, item_id) -> bool:
    return pq["live"].pop(item_id, None) is not None


def pq_pop(pq: dict):
    """(item_id, priority, payload) of the smallest live entry, or None. Stale heap entries are skipped."""
    while pq["heap"]:
        priority, seq, item_id = heapq.heappop(pq["heap"])
        live = pq["live"].get(item_id)
        if live is not None and live[1] == seq:
            del pq["live"][item_id]
            return item_id, priority, live[2]
    return None


def pq_peek(pq: dict):
    while pq["heap"]:
        priority, seq, item_id = pq["heap"][0]
        live = pq["live"].get(item_id)
        if live is not None and live[1] == seq:
            return item_id, priority, live[2]
        heapq.heappop(pq["heap"])
    return None
```

```python
pq = pq_new()
pq_push(pq, "t1", 10)
pq_push(pq, "t2", 5)
pq_push(pq, "t1", 1)            # t1's deadline moved up
pq_pop(pq)                       # ("t1", 1, None)
```

For several sort keys, push a tuple as the priority: `(deadline, -importance)`.

---

## Part 2: Retries and a dead-letter list

### Step 4: Run jobs in parallel, in order

A thread pool with `pool.map` gives bounded parallelism and keeps results in input order (see part 2 of this series).

### Step 5: Retry inside each job

Wrap the handler in a loop: try, and on an exception, wait with backoff and try again, up to `max_attempts` attempts in total.

### Step 6: Don't retry everything

A `ValueError` from bad input will fail the same way every time. A `TimeoutError` might not. Let the caller pass `retryable(error)` to choose.

### Step 7: Collect failures in a dead-letter list

A job that runs out of attempts, or hits a non-retryable error, goes into a **dead-letter** list with its error and attempt count, and its result slot becomes `None`. The batch carries on. Someone can inspect and replay the dead letters later.

### The complete snippet

```python
import time
from concurrent.futures import ThreadPoolExecutor


def run_jobs(jobs, handler, workers: int = 5, max_attempts: int = 3, backoff: float = 0.0,
             retryable=lambda error: True):
    """handler(job) for each job, `workers` at a time. A job that raises is retried (max_attempts total)
    while retryable(error); then it goes to the dead-letter list.
    Returns (results in input order with None for dead jobs, dead_letters)."""
    dead = []

    def run(job):
        for attempt in range(1, max_attempts + 1):
            try:
                return handler(job)
            except Exception as e:
                if attempt == max_attempts or not retryable(e):
                    dead.append({"job": job, "error": f"{type(e).__name__}: {e}", "attempts": attempt})
                    return None
                time.sleep(backoff * 2 ** (attempt - 1))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run, jobs))
    return results, dead
```

```python
results, dead = run_jobs(records, enrich, workers=5, max_attempts=3, backoff=0.5,
                         retryable=lambda e: not isinstance(e, ValueError))
atomic_write_json("output/results.json", results)
atomic_write_json("output/dead_letters.json", dead)
```

---

## Part 3: Token budgets for LLM batches

### Step 8: Estimate before you call

You only know a call's exact token count afterwards. Before calling, use a rough estimate: about 4 characters per token, plus your expected output length.

### Step 9: Reserve, then settle

With five threads running, checking "used < limit" and *then* calling isn't safe: all five can pass the check at once and overshoot together. Instead:

1. **Reserve** the estimate under a lock. If it doesn't fit, skip the call.
2. Make the call.
3. **Settle:** release the reservation and add the *real* usage from the response's `usage` field.

### Step 10: Report the cost

Track prompt and completion tokens separately; most providers charge different rates for each. Pass in the prices rather than hardcoding them, because they change.

### The complete snippet

```python
import threading


def new_budget(limit_tokens: int) -> dict:
    return {"limit": limit_tokens, "used": 0, "reserved": 0, "calls": 0,
            "prompt": 0, "completion": 0, "lock": threading.Lock()}


def estimate_tokens(*texts: str) -> int:
    """Rough upper-bound estimate (~4 chars per token) for reserving budget before a call."""
    return sum(len(t) for t in texts) // 4 + 1


def reserve(budget: dict, estimate: int) -> bool:
    """Reserve before calling. False -> over budget: skip the call (mark the row budget_exceeded)."""
    with budget["lock"]:
        if budget["used"] + budget["reserved"] + estimate > budget["limit"]:
            return False
        budget["reserved"] += estimate
        return True


def settle(budget: dict, estimate: int, usage=None) -> None:
    """After the call: release the reservation and record real usage (OpenAI's response["usage"])."""
    usage = usage or {}
    with budget["lock"]:
        budget["reserved"] -= estimate
        budget["used"] += usage.get("total_tokens", estimate)
        budget["prompt"] += usage.get("prompt_tokens", 0)
        budget["completion"] += usage.get("completion_tokens", 0)
        budget["calls"] += 1


def cost_usd(budget: dict, input_per_million: float, output_per_million: float) -> float:
    return round(budget["prompt"] * input_per_million / 1e6
                 + budget["completion"] * output_per_million / 1e6, 6)
```

### Step 11: Wire it around a call

```python
budget = new_budget(limit_tokens=200_000)

def classify_within_budget(item):
    text = json.dumps(item)
    estimate = estimate_tokens(SYSTEM_PROMPT, text) + 50          # + expected output
    if not reserve(budget, estimate):
        return "budget_exceeded"
    usage = None
    try:
        r = httpx.post(url, json=payload_for(text), headers=headers, timeout=10)
        usage = r.json().get("usage")
        return parse_label(r)
    finally:
        settle(budget, estimate, usage)

results = bounded_map(classify_within_budget, items, 5)
print(budget["used"], cost_usd(budget, input_per_million=0.15, output_per_million=0.60))
```

---

## Testing

```python
def test_priority_update_and_remove():
    pq = pq_new()
    for tid, d in [("a", 5), ("b", 1), ("c", 1)]:
        pq_push(pq, tid, d)
    pq_push(pq, "a", 0)
    pq_remove(pq, "c")
    assert [pq_pop(pq)[0] for _ in range(2)] == ["a", "b"]


def test_dead_letters():
    def handler(j):
        if j == "bad":
            raise ValueError("nope")
        return j.upper()
    results, dead = run_jobs(["ok", "bad"], handler, retryable=lambda e: not isinstance(e, ValueError))
    assert results == ["OK", None] and dead[0]["attempts"] == 1


def test_budget_never_overshoots():
    b = new_budget(100)
    assert reserve(b, 60) and not reserve(b, 50)
    settle(b, 60, {"total_tokens": 40})
    assert b["used"] == 40 and reserve(b, 50)
```

---

## Recap

1. **Priority queue:** `(priority, seq, id)` for FIFO ties, and lazy deletion for O(log n) updates.
2. **Worker pool:** retry only what's retryable, with backoff, and send the rest to a dead-letter list without stopping the batch.
3. **Budget:** reserve before calling, settle with real usage after, and report the cost by token type.
