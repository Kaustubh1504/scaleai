# 43. collections drills

Four small jobs from an annotation platform, each of which has a one-import
answer in `collections`. Interviewers notice when you reach for the right
container instead of hand-rolling dict bookkeeping.

## Input

* `labels`: an iterable of label strings, e.g. `["cat", "dog", "cat"]`.
* `submissions`: an iterable of dicts like `{"annotator_id": "ann_1", "task_id": "t_9"}`.
* Event timestamps are floats (seconds), recorded in non-decreasing order.

## Setup

There is no `problem_api`: tests call your functions and classes directly with
plain lists and floats, e.g. `top_labels(["cat", "dog", "cat"], 2)`. Your file
starts empty. An `if __name__ == "__main__":` block is what the Run button
executes: use it to see how `Counter.most_common` orders ties and what a
`defaultdict` lookup does to a missing key.

## Your task

Write in your file:

* `top_labels(labels: Iterable[str], n: int) -> list[tuple[str, int]]`
* `group_by_annotator(submissions: Iterable[dict]) -> dict[str, list[str]]`
* `SlidingWindowCounter(window_s: float)` with `.record(ts: float) -> None` and `.count(now: float) -> int`
* `LRUCache(capacity: int)` with `.get(key, default=None)`, `.put(key, value) -> None` and `len(cache)`

Rules:

* `top_labels`: the `n` most frequent labels as `(label, count)`, count
  descending, **ties broken by label ascending** (not by first appearance).
  `n` larger than the number of distinct labels returns all of them.
* `group_by_annotator`: `annotator_id -> [task_id, ...]` with task ids in input
  order. Return a **plain `dict`** (not a `defaultdict`), so looking up an
  unknown annotator raises `KeyError` instead of silently inserting `[]`.
* `SlidingWindowCounter.count(now)` returns how many recorded events have
  `now - window_s < ts <= now`. An event exactly `window_s` old is **out**.
  Drop expired events as you go, so memory stays bounded by the window; 200k
  records interleaved with counts must stay fast.
* `LRUCache`: `get` returns the value (or `default`) and marks the key as most
  recently used. `put` inserts or updates (an update also marks it most
  recent). When a `put` grows the cache beyond `capacity`, evict the least
  recently used key. `capacity < 1` raises `ValueError`.

## Example

```python
top_labels(["dog", "cat", "dog", "cat", "bird"], 2)   # [("cat", 2), ("dog", 2)]
group_by_annotator([{"annotator_id": "a", "task_id": "t1"}, {"annotator_id": "a", "task_id": "t2"}])
# {"a": ["t1", "t2"]}

c = SlidingWindowCounter(60); c.record(0); c.record(30); c.record(61)
c.count(61)   # 2  (ts=0 is 61s old; ts=30 and ts=61 are inside)

cache = LRUCache(2); cache.put("a", 1); cache.put("b", 2); cache.get("a"); cache.put("c", 3)
cache.get("b")   # None: "b" was least recently used
```

## Constraints

* Use the standard library (`collections`, no third-party packages).

<details><summary>Hint 1</summary>

`Counter.most_common()` orders ties by first insertion. Sort its items with
`key=lambda kv: (-kv[1], kv[0])` instead.
</details>

<details><summary>Hint 2</summary>

`deque.popleft()` from the left while `dq[0] <= now - window_s`.
`OrderedDict.move_to_end(key)` and `popitem(last=False)` are the whole LRU.
</details>

## Follow-up (talk it through)

* `functools.lru_cache` exists. When would you still write your own LRU?
* The sliding window must work across 20 API workers. What changes?
