# 27. Flatten nested JSON to CSV and back

An ops lead wants this week's annotation tasks "in a spreadsheet". The tasks
API returns nested JSON: a project object, a list of annotations each with a
bounding-box list, tags, an optional reviewer. You'll flatten each task into
dotted column paths, write one CSV with the union of all columns, and provide
the inverse so an edited spreadsheet row can be turned back into JSON.

## Input

`problem_api.load_tasks()` (file `TASKS_JSON`), three tasks like:

```json
{"task_id": "t-1",
 "project": {"id": "p-9", "name": "Street signs"},
 "annotations": [{"label": "stop_sign", "bbox": [10, 20, 50, 60], "confidence": 0.98}, ...],
 "tags": ["night", "rain"], "reviewer": null, "meta": {}}
```

## Setup

```python
from problem_api import load_tasks    # fresh list[dict] each call; file is TASKS_JSON
tasks = load_tasks()
```

The `if __name__ == "__main__":` block is what the Run button executes: print
the raw JSON and each task's top-level value types there before flattening.

## Your task

Your module must define:

* `flatten(obj: dict, sep: str = ".") -> dict[str, Any]`
* `to_csv_text(records: list[dict], sep: str = ".") -> str`
* `unflatten(flat: dict[str, Any], sep: str = ".") -> dict`

**`flatten`**
* `obj` must be a `dict` (else `TypeError`). Nested dicts join keys with `sep`;
  list items use their index: `{"tags": ["a"]}` → `{"tags.0": "a"}`. Lists of
  dicts and lists of lists recurse the same way (`"annotations.0.bbox.3"`).
* Any value that isn't a dict or list is a leaf, kept **as is** (`None`, `True`, `0.98`).
* Empty dicts and empty lists are **omitted** (they produce no column).
* Key order: depth-first, in insertion / list order.
* A dict key that is empty or contains `sep` raises `ValueError` (it would be ambiguous).
* Don't mutate the input.

**`to_csv_text`**
* Flatten every record. Columns are the union of keys in **first-seen order**
  (walk records in order, keys in flattened order, append unseen ones).
* Header row, then one row per record. Missing cells are `""`. Cells: `None` → `""`,
  `True`/`False` → `"true"`/`"false"`, anything else `str(value)`.
* Write with `csv.writer(..., lineterminator="\n")` (default quoting, so commas,
  quotes and newlines are quoted correctly). `records == []` → `""`.

**`unflatten`**
* Split each key on `sep` (an empty segment raises `ValueError`) and rebuild the nesting.
* Below the top level, a container whose child segments are **all** canonical
  non-negative integers (`"0"`, `"12"`, not `"01"`) becomes a `list`; they must be
  exactly `0..n-1` (any input order) or it's a `ValueError`. Mixing index and
  non-index children under one parent is a `ValueError`. The top level is always a dict.
* A key that is both a leaf and a prefix of another key (`"a"` and `"a.b"`) is a `ValueError`.
* Round trip: `unflatten(flatten(x)) == x` whenever `x` has no empty containers
  and no integer-looking dict keys.

## Example

```python
flatten({"id": "t-1", "tags": ["night", "rain"], "project": {"id": "p-9"}, "meta": {}})
# {"id": "t-1", "tags.0": "night", "tags.1": "rain", "project.id": "p-9"}

print(to_csv_text([{"id": 1, "ok": True}, {"id": 2, "note": "a, b"}]), end="")
# id,ok,note
# 1,true,
# 2,,"a, b"

unflatten({"a.1": "y", "a.0": "x", "b.c": None})  # {"a": ["x", "y"], "b": {"c": None}}
```

## Constraints

* Standard library only (`csv`, `io`). Never build CSV lines with `",".join(...)`.

<details><summary>Hint 1</summary>

`flatten` is one recursive helper that carries the current prefix and an output
dict: dicts recurse over their items, lists over `enumerate()`, anything else
is stored at the prefix.
</details>

<details><summary>Hint 2</summary>

For `unflatten`, first build a tree of plain dicts keyed by segment (mark leaves
so you can detect `"a"` vs `"a.b"`), then convert bottom-up: a dict whose keys
are all indexes becomes a list.
</details>

## Follow-up (talk it through)

* One task has 300 annotations: that's 1,500 columns. What would you give the ops lead instead?
* After a CSV round trip, `0.98` comes back as the string `"0.98"` and `null` as `""`. How would you preserve types?
* Why is it better to raise on a key containing `.` than to escape it?
