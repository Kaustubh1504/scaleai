# Backend Logic Patterns in Python, Step by Step: Grouping, Deduping, Voting, and Scheduling

### The small functions in the middle of every pipeline, and the bugs each one prevents

Most backend bugs aren't in the framework. They're in ten lines in the middle: a dedupe that kept the wrong row, a "latest" that meant latest to *arrive*, a vote threshold that failed on floating point, a total that was off by a cent.

This tutorial builds those functions one at a time. Each section starts with the obvious version, shows where it breaks, and ends with a function you can copy.

**What you need:** Python 3.9+. Standard library only.

---

## 1. Grouping, counting, deduping, and "latest wins"

### Step 1: Group by any key

The obvious version checks `if key not in groups` every time. `defaultdict(list)` removes that check:

```python
groups = defaultdict(list)
for order in orders:
    groups[order["customer"]].append(order)
```

Take a `key` function instead of a field name, so the same function can group by anything: `lambda o: o["created_at"].date()`.

### Step 2: Count, and break ties deterministically

`Counter(...).most_common(1)` picks arbitrarily between tied values, which depends on input order. That makes tests flaky. Sort by count descending, then by key ascending.

### Step 3: Dedupe, keeping the first

`list(set(items))` loses both the order and the "first one wins" rule. Use a set for the membership check and a list for the output.

### Step 4: "Latest" means highest version, not last to arrive

Events arrive out of order: retries, multiple producers, replays. Compare a version or timestamp that's *inside the event*. A delete is just another event (a "tombstone") that wins on version and gets filtered out at the end.

### The complete functions

```python
from collections import Counter, defaultdict


def group_by(items, key):
    out = defaultdict(list)
    for it in items:
        out[key(it)].append(it)
    return dict(out)


def top_counts(items, key, n: int = 1):
    """Most common first; ties broken by the key ascending (deterministic)."""
    return sorted(Counter(key(it) for it in items).items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def dedupe(items, key):
    """Keep the first occurrence of each key, preserve order."""
    seen, out = set(), []
    for it in items:
        k = key(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def latest_by(items, key, version, deleted=lambda it: False):
    """Highest version wins regardless of arrival order; tombstones removed at the end."""
    best = {}
    for it in items:
        k = key(it)
        if k not in best or version(it) > version(best[k]):
            best[k] = it
    return [it for it in best.values() if not deleted(it)]
```

```python
latest_by(events, key=lambda e: e["id"], version=lambda e: e["version"],
          deleted=lambda e: e.get("deleted", False))
```

---

## 2. Joining and diffing

### Step 1: Join with a lookup dict, not a nested loop

A nested loop over 10,000 × 10,000 rows is 100 million comparisons. Building an index first makes the join one pass over each list.

### Step 2: Report unmatched rows, never drop them silently

A missing user is usually a data problem someone needs to hear about. Return the unmatched rows alongside the result.

### Step 3: Diff two snapshots with set algebra

Use this for sync jobs, audits, and "what changed since yesterday": added, removed, changed.

```python
def left_join(left, right, left_key, right_key, as_field: str):
    """Attach the matching right row (or None) to a copy of each left row. Returns (rows, unmatched)."""
    index = {right_key(r): r for r in right}
    rows, unmatched = [], []
    for l in left:
        match = index.get(left_key(l))
        if match is None:
            unmatched.append(l)
        rows.append({**l, as_field: match})
    return rows, unmatched


def diff(old: dict, new: dict) -> dict:
    """Snapshots keyed by id -> added / removed / changed ids (sorted)."""
    o, n = set(old), set(new)
    return {"added": sorted(n - o), "removed": sorted(o - n),
            "changed": sorted(k for k in o & n if old[k] != new[k])}
```

```python
rows, unknown = left_join(tasks, users, lambda t: t["user_id"], lambda u: u["user_id"], "user")
```

---

## 3. Majority vote with a threshold

Suppose several human annotators label each item, and you need one answer. The rules:

- Fewer than 3 votes: **insufficient**.
- The top label has at least two-thirds of the votes: **agreed**.
- Otherwise: **disputed**. Send it to a tiebreaker, such as an LLM or a senior reviewer.

### Step 1: The float trap

```python
if top / total >= 0.67:      # 2/3 = 0.6666... -> exactly two-thirds FAILS
if top / total >= 2 / 3:     # works here, but float comparisons are fragile in general
```

### Step 2: Compare with integers

`top / total >= 2/3` is the same as `top * 3 >= total * 2`. Integers have no rounding, so exactly two-thirds always counts as agreed.

### Step 3: Make ties deterministic, and handle zero votes

Sort by count, then by label. With no votes, return `agreement: None` rather than dividing by zero.

```python
from collections import Counter


def consensus(labels: list[str], min_votes: int = 3, threshold: tuple[int, int] = (2, 3)) -> dict:
    """Majority vote. threshold=(2, 3) means top label needs >= 2/3 of votes (integer math, no float bugs)."""
    votes = Counter(labels)
    total = sum(votes.values())
    if not total:
        return {"votes": {}, "total": 0, "agreement": None, "status": "insufficient", "label": None}
    label, top = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    out = {"votes": dict(votes), "total": total, "agreement": round(top / total, 2)}
    if total < min_votes:
        return {**out, "status": "insufficient", "label": None}
    num, den = threshold
    if top * den >= total * num:
        return {**out, "status": "agreed", "label": label}
    return {**out, "status": "disputed", "label": None}
```

```python
consensus(["spam", "spam", "safe"])      # agreed, label "spam", agreement 0.67
consensus(["spam", "safe", "violence"])  # disputed
consensus(["spam", "spam"])              # insufficient (only 2 votes)
```

---

## 4. Time zones and money

### Time: store UTC, convert at the edge

An order at 20:00 UTC on March 3 is a **March 4** order in India. If you group by `created_at.date()` on UTC timestamps, your "orders per day" report is wrong for every user outside UTC. Convert to the user's time zone only when grouping or displaying.

### Money: integer cents, round once

`0.1 + 0.2 != 0.3` in floating point. Store money as integer cents, and convert with `Decimal` exactly once, at the end.

```python
from collections import Counter
from datetime import timezone
from decimal import ROUND_HALF_UP, Decimal


def count_per_local_day(timestamps, tz=timezone.utc) -> dict:
    """Aware datetimes (store UTC) -> {"YYYY-MM-DD": count} in the given timezone."""
    return dict(Counter(ts.astimezone(tz).date().isoformat() for ts in timestamps))


def cents_to_dollars(cents: int) -> Decimal:
    """Keep money as integer cents; convert/round once at the end."""
    return (Decimal(cents) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

```python
IST = timezone(timedelta(hours=5, minutes=30))
count_per_local_day([order["created_at"] for order in orders], IST)
cents_to_dollars(sum(o["total_cents"] for o in orders))
```

---

## 5. Chunking and graph walks

### Chunk for batch APIs

Most bulk endpoints cap batch size, often at 100 or 500. (On Python 3.12+, `itertools.batched` does this lazily.)

### Breadth-first search: mark nodes as seen when you queue them

Mark nodes as seen when you **queue** them, not when you **visit** them. Otherwise a node reachable from many parents gets queued many times. Take a `neighbors` function, so the same code works for an org chart, a crawler, or a dependency tree.

```python
from collections import deque


def chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def bfs(start, neighbors, max_depth=None) -> list[tuple]:
    """neighbors(node) -> iterable. Returns [(node, depth)] in visit order; mark seen on enqueue."""
    queue, seen, order = deque([(start, 0)]), {start}, []
    while queue:
        node, depth = queue.popleft()
        order.append((node, depth))
        if max_depth is not None and depth >= max_depth:
            continue
        for nxt in neighbors(node):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, depth + 1))
    return order
```

```python
for batch in chunks(user_ids, 100):
    api.bulk_update(batch)

graph = {"root": ["a", "b"], "a": ["b"], "b": ["root"]}
bfs("root", lambda n: graph.get(n, []), max_depth=2)
```

---

## 6. Scheduling tasks with dependencies and deadlines

### The problem

You have jobs that depend on other jobs, each with a deadline. Run every job after its dependencies, and among the jobs that are ready, always pick the most urgent.

### Step 1: Count each job's prerequisites

For every job, `indegree` counts the dependencies that haven't finished yet. A job with `indegree == 0` is ready to run.

### Step 2: Keep the ready jobs in a heap

A heap ordered by deadline always gives you the most urgent ready job in O(log n).

### Step 3: Finishing a job may unlock others

When a job runs, decrement the count for each job that depends on it. Any job that reaches zero goes into the heap.

### Step 4: Detect cycles for free

If some jobs never reach zero, they depend on each other in a loop, and fewer jobs come out than went in.

```python
import heapq
from collections import defaultdict


def schedule(tasks: dict) -> list:
    """{id: {"deadline": int, "deps": [ids]}} -> run order: deps first, earliest deadline among ready.
    Raises ValueError on unknown deps or a cycle. O((V + E) log V)."""
    indegree = {t: 0 for t in tasks}
    children = defaultdict(list)
    for t, spec in tasks.items():
        for d in spec["deps"]:
            if d not in tasks:
                raise ValueError(f"{t} depends on unknown task {d}")
            children[d].append(t)
            indegree[t] += 1
    ready = [(tasks[t]["deadline"], t) for t in tasks if indegree[t] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        _, t = heapq.heappop(ready)
        order.append(t)
        for c in children[t]:
            indegree[c] -= 1
            if indegree[c] == 0:
                heapq.heappush(ready, (tasks[c]["deadline"], c))
    if len(order) != len(tasks):
        raise ValueError("cycle in dependencies")
    return order
```

```python
schedule({
    "deploy":  {"deadline": 5, "deps": ["build", "migrate"]},
    "build":   {"deadline": 3, "deps": []},
    "migrate": {"deadline": 1, "deps": []},
    "notify":  {"deadline": 9, "deps": ["deploy"]},
})
# -> ['migrate', 'build', 'deploy', 'notify']
```

This is Kahn's topological sort with a priority queue, and it runs in O((V + E) log V).

---

## Recap

Most of these patterns come down to four habits:

1. **Be deterministic:** tie-breaks, versions instead of arrival order, sorted output.
2. **Don't mutate inputs:** `{**row, "user": match}` builds a copy.
3. **Report problems instead of dropping them:** unmatched rows, unknown dependencies, cycles.
4. **Avoid floats where exactness matters:** integer comparisons for thresholds, integer cents for money.
