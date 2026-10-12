# 30. Integrity checks across entities

Before the weekly payout run, finance wants a report of everything in the
labeling export that **can't be right**: statuses nobody defined, confidences
of 1.5, submissions for tasks that don't exist, work submitted before the task
was created, annotators working on projects they were never assigned to, and
records exported twice. You don't fix anything here; you produce a precise,
sorted list of violations a human can act on.

## Input

`problem_api.load_dataset()` returns the export (`data/dataset.json`):

```json
{
  "annotators":  [{"id": "A1", "name": "Ada", "status": "active", "projects": ["P1", "P2"]}, ...],
  "tasks":       [{"id": "T1", "project_id": "P1", "status": "open", "created_at": "2024-03-01T08:00:00Z",
                   "completed_at": null, "reward_cents": 120}, ...],
  "submissions": [{"id": "S1", "task_id": "T1", "annotator_id": "A1", "submitted_at": "2024-03-01T09:00:00Z",
                   "confidence": 0.9, "status": "accepted"}, ...]
}
```

Every record has a string `id`; any other field may be missing or have the
wrong type (treat a missing field as `null`).

## Setup

```python
from problem_api import load_dataset   # fresh dict each call; file is DATASET_PATH
data = load_dataset()
```

The `if __name__ == "__main__":` block is what the Run button executes: print
every record of each entity there before deciding what "wrong" means.

## Your task

Your module must define:

* `class Violation(NamedTuple)`: fields, in this order, `entity: str`
  (`"annotator"` | `"task"` | `"submission"`), `id: str`, `rule: str`,
  `detail: str` (human-readable, non-empty; tests don't check its wording).
* `check(dataset: dict) -> list[Violation]`

Return every violation, **sorted** by `(entity, id, rule, detail)` (plain
tuple order, so `"S10"` sorts before `"S2"`). Don't modify `dataset`.

| entity | rule | when |
|---|---|---|
| all | `duplicate` | the id appears more than once and every copy is identical (`==`) |
| all | `conflicting_duplicate` | the id appears more than once and some copy differs |
| annotator | `bad_status` | status not in `active, suspended, offboarded` |
| task | `bad_status` | status not in `open, in_progress, completed, cancelled` |
| task | `bad_reward` | `reward_cents` is not an `int` `>= 0` (`bool` and `"100"` are not ints) |
| task | `bad_timestamp` | `created_at` invalid, or `completed_at` non-null and invalid (one violation per bad field) |
| task | `missing_completed_at` | status is `completed` and `completed_at` is null |
| task | `completed_before_created` | both valid and `completed_at < created_at` |
| submission | `bad_status` | status not in `pending, accepted, rejected` |
| submission | `bad_confidence` | not an `int`/`float` (not `bool`, not NaN) with `0 <= c <= 1` |
| submission | `bad_timestamp` | `submitted_at` invalid |
| submission | `unknown_task` / `unknown_annotator` | `task_id` / `annotator_id` not among the ids in the dataset |
| submission | `submitted_before_task_created` | task known, both timestamps valid, `submitted_at < task.created_at` |
| submission | `annotator_not_on_project` | task and annotator known, `task.project_id` not in `annotator.projects` |

* **Valid timestamp**: an ISO 8601 string **with** `Z` or a `±HH:MM` offset.
  Compare instants, not strings (`"2024-03-01T11:30:00+05:00"` is before
  `"2024-03-01T10:00:00+02:00"`). A naive string like `"2024-03-01T08:00:00"`
  is invalid: you can't tell which instant it is.
* **Duplicates** are reported once per id, however many copies there are. All
  other rules, and all lookups by id, use the **first** occurrence only (so a
  duplicated record's problems are reported once).
* A record that breaks some rules still exists: a submission pointing at a
  task with a bad status is not `unknown_task`.

## Example

```python
check(load_dataset())[:4]
# [Violation("annotator", "A2", "duplicate", ...),
#  Violation("annotator", "A3", "bad_status", ...),
#  Violation("annotator", "A5", "conflicting_duplicate", ...),
#  Violation("submission", "S1", "duplicate", ...)]
```

## Constraints

* Standard library only. Each check is independent: one bad field must not
  hide a different rule on the same record.

<details><summary>Hint 1</summary>

Index each entity by id first (`setdefault` keeps the first copy) and collect all copies per id to decide `duplicate` vs
`conflicting_duplicate`. Then the cross-entity checks are dict lookups.
</details>

<details><summary>Hint 2</summary>

`isinstance(True, int)` is `True`. Parse timestamps once into aware
`datetime`s (or `None`) and only compare when both sides parsed.
</details>

## Follow-up (talk it through)

* This dataset has 30 records; production has 50 million submissions. What
  changes (streaming, a database, what you hold in memory)?
* Which of these rules would you enforce at write time (schema, foreign keys,
  check constraints) so the report becomes unnecessary?
* Finance asks for "the" correct value of a `conflicting_duplicate`. What do
  you need to know to answer that?
