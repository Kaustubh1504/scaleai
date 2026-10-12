# 48. Aggregations: plain Python vs pandas

Finance wants three numbers from the payouts ledger: total per annotator, the
top earners, and a project-by-month pivot. In the interview you may not have
pandas (or be asked not to use it), so the **plain-Python versions are graded**.
pandas is a nice-to-have: write the `_pd` versions too if you know it. Their
tests are skipped when pandas isn't installed (it isn't, here).

## Input

`data/payouts.csv`, loaded for you by `problem_api.load_rows()`:

```
date,annotator,project,amount_cents
2024-01-01,ann_ada,docs,150
2024-01-03,ann_bo,cars,275
```

`load_rows()` gives `[{"date": "2024-01-01", "annotator": "ann_ada", "project": "docs", "amount_cents": 150}, ...]`
(`amount_cents` already an `int`). Your functions take these rows, in any order.

## Setup

```python
from problem_api import load_rows
rows = load_rows()          # tests use this plus small hand-written row lists
```

Your file starts empty. An `if __name__ == "__main__":` block is what the Run
button executes: use it to print the row count and the first few rows.

## Your task

Write in your file (graded):

* `total_by_annotator(rows: list[dict]) -> dict[str, int]`
* `top_n_annotators(rows: list[dict], n: int) -> list[tuple[str, int]]`
* `monthly_pivot(rows: list[dict]) -> dict[str, dict[str, int]]`

Optional, same signatures and return values, using pandas inside:
`total_by_annotator_pd`, `top_n_annotators_pd`, `monthly_pivot_pd`.

Rules:

* `total_by_annotator`: annotator -> total cents, keys in ascending order.
* `top_n_annotators`: the `n` highest totals as `(annotator, cents)`, total
  descending, ties by annotator ascending.
* `monthly_pivot`: project -> {month -> cents}, where month is `"YYYY-MM"`
  from `date`. Projects in ascending order; every project has **every month
  that appears anywhere in the rows**, ascending, with `0` where it had no payouts.
* Return plain `int`s (not numpy ints) from the `_pd` versions too.
* Empty input: `{}`, `[]`, `{}`.

## Example

```python
rows = [{"date": "2024-01-05", "annotator": "a", "project": "cars", "amount_cents": 100},
        {"date": "2024-02-01", "annotator": "b", "project": "docs", "amount_cents": 250},
        {"date": "2024-02-09", "annotator": "a", "project": "cars", "amount_cents": 150}]
total_by_annotator(rows)   # {"a": 250, "b": 250}
top_n_annotators(rows, 1)  # [("a", 250)]
monthly_pivot(rows)        # {"cars": {"2024-01": 100, "2024-02": 150}, "docs": {"2024-01": 0, "2024-02": 250}}
```

## Constraints

* The graded functions must not import pandas (it's not installed).
* Import pandas **inside** the `_pd` functions, so your file still imports without it.

<details><summary>Hint 1</summary>

`defaultdict(int)` for totals. For the pivot, first collect the sorted set of
all months (`date[:7]`), then give each project a zero-filled dict over them.
</details>

<details><summary>Hint 2</summary>

pandas: `groupby("annotator")` + `sum()` for totals, and `pivot_table(...,
aggfunc="sum", fill_value=0)` on a derived month column for the pivot. Convert
results back with `int(v)` so you return plain ints.
</details>

## Follow-up (talk it through)

* At what data size would you stop doing this in Python and push it into SQL or pandas?
* The ledger has 50M rows and doesn't fit in memory. How would you compute these?
