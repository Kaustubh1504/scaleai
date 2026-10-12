# 26. Salvage a messy JSONL log

An LLM-judge worker scores annotator submissions and appends one JSON object
per line to `labels.log`. Three versions of the worker have written to the
same file: one says `user_id`, one `userId`, one `uid`; scores show up as
`0.9`, `"0.9"` or `"90%"`. And sometimes the model wrapped its answer in a
markdown code fence, which the worker dumped verbatim. Recover every record
you safely can, and report the rest by line number.

## Input

`problem_api.sample_text()` (the file `LABELS_LOG`):

````
 1  {"user_id": "u1", "score": 0.9, "label": "positive"}
 2  {"userId": "u2", "score": "0.75", "label": "neutral"}
 3
 4  ```json {"uid": "u3", "score": "90%", "label": "positive"} ```
 5  {"user_id": "u4", "score": 0.5, "label": "negative",}
 6  ```json
 7  {"user_id": "u5",
 8   "score": 1,
 9   "label": "positive"}
10  ```
11  [1, 2, 3]
...
````

## Setup

```python
from problem_api import sample_text    # str contents of LABELS_LOG (a pathlib.Path)
text = sample_text()
```

The `if __name__ == "__main__":` block is what the Run button executes: print
every line with its number and `repr` there before parsing.

## Your task

Your module must define:

* `parse_jsonl(text: str) -> tuple[list[dict], list[dict]]`: returns
  `(records, errors)`; each error is `{"line": int, "reason": str}`.

**Lines and fences** (lines are `text.splitlines()`, numbered from 1; compare stripped):
* Blank lines are skipped.
* **Fence opener**: a line that is exactly ` ``` ` or ` ```json ` (tag case-insensitive).
  The following lines up to the next line that is exactly ` ``` ` are joined with
  `"\n"` and parsed as **one** JSON value, reported at the opener's line. If no
  closing fence follows, report `"unclosed_fence"` at the opener and stop (the
  remaining lines belong to the broken block).
* **One-line fence**: a line starting with ` ``` ` (optionally ` ```json `) and ending
  with ` ``` `: parse what's between them.
* Any other line is parsed as JSON on its own.

**Errors**, one per record at most, checked in this order:

| reason | when |
|---|---|
| `invalid_json` | `json.loads` fails (trailing commas are **not** repaired) |
| `not_object` | valid JSON but not a `dict` |
| `missing_user_id` | none of `user_id`, `userId`, `uid` is present with a non-null value |
| `invalid_user_id` | a present id isn't a non-empty string or an int (bools don't count) |
| `conflicting_user_id` | present ids disagree after normalizing (`7` and `"7"` agree) |
| `invalid_score` | `score` can't be read as a number in `[0, 1]` |

**Normalizing a good record**
* `user_id`: the string (stripped), or `str(int)`. The alias keys are removed;
  only `user_id` remains.
* `score`: missing or `null` → `None`. An int/float (not bool) → `float`. A string
  is stripped; if it ends in `%`, the number before it divided by 100; else
  `float(s)`. Non-finite or outside `[0, 1]` → `invalid_score`. Any other type → `invalid_score`.
* Every other key is kept unchanged. `score` is always present in the output.
* `records` and `errors` are in file order.

## Example

```python
records, errors = parse_jsonl(sample_text())
records[2]   # {"user_id": "u3", "score": 0.9, "label": "positive"}   (line 4, fenced, uid, "90%")
errors[0]    # {"line": 5, "reason": "invalid_json"}
```

## Constraints

* `json` and `re` only. Don't "fix" broken JSON with regexes: a guessed repair is
  a silently wrong label.

<details><summary>Hint 1</summary>

Walk the lines with an index and a `while` loop, not a `for` loop: a fence
opener has to consume the lines after it.
</details>

<details><summary>Hint 2</summary>

Split the work in two: one step turns lines into `(line_no, payload or error)`
pairs, a second turns a parsed object into a record or an error reason. Each
half is easy to test on its own.
</details>

## Follow-up (talk it through)

* `invalid_json` lines from the LLM are 2% of the log. Retry the model, drop them, or send them to a human? What would you measure?
* Where should the alias mapping live so the next schema change isn't a code change?
* Why is an unclosed fence handled by stopping, not by parsing the remaining lines individually?
