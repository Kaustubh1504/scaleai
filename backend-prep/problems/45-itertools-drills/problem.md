# 45. itertools drills

Five one-liners you'll want when crunching API results: group, batch, flatten,
diff and running-total. Each maps to an `itertools` function, and two of them
have well-known traps.

## Input

* `tasks`: an iterable of dicts like `{"id": "t_1", "project": "p_cars"}`, in **any order**.
* Everything else: plain iterables (lists, generators, possibly endless).

## Setup

There is no `problem_api`: tests call your functions directly with lists,
one-shot iterators and endless generators, e.g. `batched(range(7), 3)`. Your file
starts empty. An `if __name__ == "__main__":` block is what the Run button
executes: use it to see `groupby`'s trap on unsorted input for yourself.

## Your task

Write in your file:

* `group_by_project(tasks: Iterable[dict]) -> dict[str, list[str]]`
* `batched(iterable: Iterable[T], n: int) -> Iterator[list[T]]` (a generator)
* `flatten_once(nested: Iterable[Iterable[T]]) -> list[T]`
* `deltas(values: Iterable[float]) -> list[float]`
* `running_totals(values: Iterable[float]) -> list[float]`

All of them accept one-shot iterators as well as lists. Rules:

* `group_by_project`: `project -> [task id, ...]` using `itertools.groupby`.
  Keys in ascending project order; ids keep their input order within a project.
  The input is **not sorted**.
* `batched`: yield lists of `n` items (the last one may be shorter). It must
  be **lazy**: never read more than `n` items ahead, so it works on an endless
  generator. `n < 1` raises `ValueError`. Yield lists, not tuples (so not
  `itertools.batched`, which also needs 3.12).
* `flatten_once`: flatten exactly **one** level: `[[1, [2]], [3]] -> [1, [2], 3]`.
* `deltas`: differences between consecutive values, `b - a`. Fewer than two
  values gives `[]`.
* `running_totals`: cumulative sums, same length as the input.

## Example

```python
group_by_project([{"id": "t1", "project": "b"}, {"id": "t2", "project": "a"}, {"id": "t3", "project": "b"}])
# {"a": ["t2"], "b": ["t1", "t3"]}
list(batched(range(7), 3))      # [[0, 1, 2], [3, 4, 5], [6]]
deltas([10, 13, 13, 20])        # [3, 0, 7]
running_totals([3, 1, 4])       # [3, 4, 8]
```

## Constraints

* Use `itertools` (`groupby`, `islice`, `chain.from_iterable`, `pairwise`,
  `accumulate`); no index arithmetic loops.

<details><summary>Hint 1</summary>

`groupby` only groups **adjacent** equal keys. On unsorted input you get the
same key twice, and a dict comprehension silently keeps only the last group.
`sorted(tasks, key=...)` is stable, so ids keep their order.
</details>

<details><summary>Hint 2</summary>

Turn the input into an iterator once, then loop taking `list(islice(it, n))`
until that comes back empty. Call `iter()` first: `islice` on a list restarts
from the beginning every time.
</details>

## Follow-up (talk it through)

* You're batching 10M ids into `?ids=` requests of 100. Why does laziness matter here?
* When is `groupby` (sort + group) better than a `defaultdict(list)`, and when worse?
