# 05: Task Processor (30 min)

Build it from scratch in Python. There's no starter code. Put your solution in **`processor.py`**
in this folder (it must define `class TaskProcessor`) and your tests in `tests/`. Use only the
standard library (`heapq`, `collections`, ...). Docs are fine; AI assistants are not.

| Part | Time | What |
|---|---|---|
| 1 | 10 min | `add_task` / `consume_task`: earliest deadline first, stable ties, duplicate ids |
| 2 | 12 min | Subtask dependencies: a task is ready only once all its subtasks are consumed |
| 3 | 8 min | `update_deadline` with lazy deletion |
| — | after | Discussion |

```python
class TaskProcessor:
    def __init__(self) -> None: ...
    def add_task(self, task_id: str, deadline: float, subtasks: list[str] | None = None) -> None: ...
    def consume_task(self) -> str | None: ...
    def update_deadline(self, task_id: str, new_deadline: float) -> None: ...   # Part 3
    def __len__(self) -> int: ...
```

### Terms

* **pending**: added with `add_task` and not yet returned by `consume_task`.
* **consumed**: returned by `consume_task`. A consumed task never comes back.
* **ready**: pending, and (from Part 2 on) every one of its subtasks is consumed.
* **add order**: the order of successful `add_task` calls. It's fixed when the task is added and
  never changes (not even in Part 3).

---

## Part 1: earliest deadline first (10 min)

In Part 1 every task is ready. You can ignore `subtasks` (tests pass `None`, `[]`, or nothing).

| Method | Behaviour |
|---|---|
| `add_task(task_id, deadline, subtasks=None)` | Adds a pending task. `deadline` is an `int` or `float` (may be negative or 0). Returns `None`. |
| `consume_task()` | Removes and returns the `task_id` of the **ready** task with the **smallest deadline**. Ties go to the task **added first**. Returns `None` if no task is ready (including when empty). |
| `__len__()` | Number of **pending** tasks (ready or not). |

### Errors

| Case | Result |
|---|---|
| `task_id` is already pending | `ValueError` |
| `task_id` was already consumed | `ValueError` (ids are never reused) |

A call that raises must leave the processor unchanged.

### Complexity

Use a heap (`heapq`). `add_task` and `consume_task` must be **O(log n)** (amortized). Scanning
all tasks on every call is too slow: the grader does 200,000 adds and 200,000 consumes with a
2-second limit.

### Example 1

```python
p = TaskProcessor()
p.add_task("a", 5)
p.add_task("b", 2)
p.add_task("c", 5)
p.add_task("d", 1)
len(p)            # 4
p.consume_task()  # "d"
p.consume_task()  # "b"
p.consume_task()  # "a"   (ties with "c" at 5; "a" was added first)
p.consume_task()  # "c"
p.consume_task()  # None
p.add_task("a", 0)  # ValueError: "a" was already consumed
```

---

## Part 2: subtask dependencies (12 min)

`subtasks` is a list of task ids that must all be **consumed** before this task is ready.
Subtasks are ordinary tasks, added with their own `add_task` call.

| Case | Rule |
|---|---|
| Subtask is consumed | met |
| Subtask is pending (ready or not) | unmet |
| Subtask was never added | unmet (it may be added later, even after the parent) |
| Subtask was already consumed when the parent is added | met (the parent may be ready at once) |
| Same id listed more than once | counts once |
| `None` or `[]` | no prerequisites: ready at once |
| Cycle (`a` needs `b`, `b` needs `a`), including a task listing itself | those tasks (and anything depending on them) **never** become ready. No error. They still count in `len`. |

Among ready tasks, Part 1's order applies: smallest deadline, then add order. A task that
becomes ready late keeps its original add order for ties. A not-ready task's deadline doesn't
matter until it becomes ready.

### Required design (complexity)

Don't re-scan tasks to find out what became ready. Keep:

* for each pending task, a count of **distinct unmet subtasks**;
* a reverse map **subtask id → parents waiting on it** (the subtask may not exist yet);
* a heap that holds **only ready** tasks.

When a task is consumed, decrement each waiting parent's count; push a parent onto the heap
when its count reaches 0. `consume_task` must stay **O(log n)** amortized (plus the number of
parents it unlocks). The grader runs a 100,000-task chain added in reverse order and one task
with 100,000 subtasks, each with a 2-second limit.

### Example 2

```python
p = TaskProcessor()
p.add_task("build", 1, ["fetch", "lint"])
p.add_task("lint", 3)
p.add_task("fetch", 2, ["auth"])     # "auth" doesn't exist yet
p.add_task("deploy", 0, ["build"])
p.add_task("auth", 9)
len(p)            # 5
p.consume_task()  # "lint"    ready: lint(3), auth(9)
p.consume_task()  # "auth"    -> fetch is now ready
p.consume_task()  # "fetch"   -> build is now ready (lint and fetch consumed)
p.consume_task()  # "build"   -> deploy is now ready
p.consume_task()  # "deploy"
p.consume_task()  # None
```

`deploy` has the earliest deadline (0) but comes out last: deadlines only order **ready** tasks.

---

## Part 3: `update_deadline` (8 min)

| Method | Behaviour |
|---|---|
| `update_deadline(task_id, new_deadline)` | Sets the task's deadline. Returns `None`. Works for **ready and not-ready** pending tasks; a not-ready task uses the new deadline once it becomes ready. Repeated updates: the last one wins. |

| Case | Result |
|---|---|
| `task_id` was never added (including an id only ever named as a subtask) | `KeyError` |
| `task_id` was already consumed | `KeyError` |

**Tie-break after an update still uses the original add order**, not the order of the
updates. If `a` was added before `b` and both end up at deadline 5, `a` comes out first, no
matter which was updated or when.

### Required design: lazy deletion

Don't search the heap and re-heapify. Push a **new** entry with the new deadline and leave the
old one in place. When popping, **skip stale entries** (detect them with a per-task version
counter, or by comparing against a current-deadline map). A task must never be returned twice,
and an old entry must never make a task come out at its old deadline. `update_deadline` must
be **O(log n)**: the grader does 50,000 updates on one task in a 100,000-task processor, then
drains it, within 2 seconds.

### Example 3

```python
p = TaskProcessor()
p.add_task("x", 10)
p.add_task("y", 20)
p.add_task("z", 30, ["x"])
p.add_task("w", 20)
p.update_deadline("w", 5)
p.update_deadline("y", 5)   # ties with w; y was added before w
p.update_deadline("z", 1)   # z isn't ready yet: fine
p.consume_task()  # "y"
p.consume_task()  # "w"
p.consume_task()  # "x"     -> z is now ready, at deadline 1
p.consume_task()  # "z"
p.consume_task()  # None
p.update_deadline("x", 0)     # KeyError: consumed
p.update_deadline("nope", 1)  # KeyError: never added
```

---

## Discussion (out loud)

1. Why is lazy deletion better than "find the entry, remove it, `heapify`"? (O(log n) vs O(n)
   per update; `heapq` has no decrease-key.)
2. Stale entries pile up: 50k updates to one task leave 50k dead entries. How much memory is
   that, and when would you compact (e.g. rebuild the heap when stale > live)? What does a
   rebuild cost?
3. Thread safety: several workers call `consume_task` at once. Where does the lock go? Can two
   workers get the same task? What about blocking until a task is ready (`Condition`)?
4. How does this map to a real scheduler (Airflow / Dagster DAGs, Celery chains)? What's a
   topological order and how is your ready set a lazy one (Kahn's algorithm)?
5. If cycles had to be **rejected** in `add_task`, how would you detect them, and what does
   that cost? (DFS from the new task, but subtasks can be added later.) How would you report
   tasks that can never run?
6. Failures and retries: a consumed task fails. How would you re-queue it, and what happens to
   parents waiting on it? At-least-once vs. exactly-once.
7. Persisting the queue across restarts; distributing it (Redis sorted set, a DB table with
   `SELECT ... FOR UPDATE SKIP LOCKED`).

---

## Tests you must write (in `tests/`)

1. Example 1, 2 and 3 above, exactly.
2. Ties: same deadline comes out in add order (use ids whose alphabetical order is the
   opposite of add order).
3. `consume_task()` on an empty processor, and when tasks exist but none is ready → `None`.
4. Duplicate id → `ValueError`, both while pending and after it's been consumed; state unchanged.
5. A subtask added **after** its parent; a subtask already consumed before the parent is added.
6. Diamond dependency (`top` needs `left` and `right`, both need `base`).
7. Duplicate ids in a subtask list; a two-task cycle stays pending forever and `len` counts it.
8. `update_deadline` earlier, later, repeatedly, on a not-ready task; `KeyError` for unknown and
   consumed ids; a tie after an update uses add order.
9. A timing test: 100k+ operations finish in well under a second or two.
10. (Bonus) A randomized test against a brute-force version of the processor.

## Grading (only after you're done)

```bash
python -m pytest _grader -q
```
