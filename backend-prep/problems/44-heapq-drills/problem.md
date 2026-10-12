# 44. heapq drills

Three heap jobs from an annotation platform: a leaderboard, a merged log tail
across shards, and a task queue. `heapq` is the tool for all three, and each
has a classic trap.

## Input

* `scores`: an iterable of `(annotator_id, score)` tuples.
* Log streams: iterables of dicts like `{"ts": 1700000003.5, "shard": "a", "msg": "..."}`,
  each **already sorted by `ts`**. They may be huge or endless.

## Setup

There is no `problem_api`: tests call your functions directly with lists,
generators (including endless ones) and dicts, e.g. `top_k([("a1", 0.9)], 1)`.
Your file starts empty. An `if __name__ == "__main__":` block is what the Run
button executes: use it to watch `heapq` pop tuples and to see the `TypeError`
when two equal keys force it to compare dicts.

## Your task

Write in your file:

* `top_k(scores: Iterable[tuple[str, float]], k: int) -> list[tuple[str, float]]`
* `merge_logs(*streams: Iterable[dict]) -> Iterator[dict]`
* `TaskScheduler()` (no arguments) with `.submit(task_id: str, priority: int, payload: dict | None = None) -> None`, `.pop() -> tuple[str, dict | None]` and `len(scheduler)`

Rules:

* `top_k`: the `k` best entries, **score descending, then annotator id
  ascending**. `k <= 0` returns `[]`; `k` larger than the input returns all.
* `merge_logs`: yield every record from all streams in `ts` order. Records
  with equal `ts` come out in the order of the streams passed (first stream
  first). It must be **lazy**: it may only pull from a stream when it needs
  that stream's next record, so it works on endless generators. No streams,
  or only empty ones, yields nothing.
* `TaskScheduler.pop()` returns `(task_id, payload)` for the **highest
  priority** task; among equal priorities, the one **submitted first**.
  `pop()` on an empty scheduler raises `IndexError`. Payloads are arbitrary
  dicts (they are not comparable with `<`).

## Example

```python
top_k([("a1", 0.9), ("a2", 0.95), ("a3", 0.9)], 2)       # [("a2", 0.95), ("a1", 0.9)]

s = TaskScheduler()
s.submit("t_b", 1, {"x": 1}); s.submit("t_a", 1, {"x": 2}); s.submit("t_z", 5)
s.pop(), s.pop(), s.pop()   # ("t_z", None), ("t_b", {"x": 1}), ("t_a", {"x": 2})
```

## Constraints

* Use `heapq` (`nsmallest`, `merge`, `heappush`/`heappop`). Don't sort the
  whole log streams.

<details><summary>Hint 1</summary>

Use `heapq.nsmallest` with a key that negates the score and then uses the id:
negating gives "largest first" from a min-heap API.
</details>

<details><summary>Hint 2</summary>

Push `(-priority, seq, task_id, payload)` where `seq` comes from
`itertools.count()`. The counter makes equal priorities FIFO *and* means
Python never compares two payload dicts.
</details>

## Follow-up (talk it through)

* `heapq.nsmallest(k, ...)` vs `sorted(...)[:k]`: when does each win?
* How would you support "cancel task t_42" in the scheduler without an O(n) scan?
