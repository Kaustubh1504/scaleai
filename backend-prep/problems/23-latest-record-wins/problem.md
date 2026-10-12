# 23. Latest record wins (CDC stream)

The task service publishes every change to a task as a new **version** on a
change-data-capture stream. Your consumer has to rebuild the current state of
every task from that stream. Events arrive **out of order**, producers in
different regions stamp times with different offsets, a delete is a
**tombstone** event, and occasionally two producers emit the same version at
the same instant with different content. That last case is a bug you must
surface, not hide.

## Input

A list of events (see `problem_api.STREAM`), in arrival order:

```python
{"id": "task_2", "version": 2, "updated_at": "2024-05-01T11:30:00+02:00",
 "deleted": False, "status": "in_progress", "assignee": "ann_7"}
{"id": "task_10", "version": 2, "updated_at": "2024-05-01T10:00:00Z", "deleted": True}
```

* `updated_at` is ISO 8601 with `Z` or `±HH:MM`, whole seconds.
* `deleted` may be missing, which means `False`. Any other keys are the record's fields.

## Setup

```python
from problem_api import STREAM      # 11 events, in arrival order
```

No HTTP: a pure function over a list. The `if __name__ == "__main__":` block
is what the Run button executes: print the stream grouped by id there (a
stable sort keeps arrival order within an id) before writing any logic.

## Your task

Your module must define:

* `materialize(events: list[dict]) -> tuple[list[dict], list[dict]]`

Returns `(records, conflicts)`.

* **Winner per id**: the event with the latest `updated_at` **instant**
  (compare in UTC, not as strings); if tied, the higher `version`; if *both*
  tie, the event that appears **later** in the input.
* If the winner is a tombstone (`deleted` true), the id is **absent** from
  `records`. An older tombstone doesn't remove a newer live version, and a
  newer live version brings a deleted id back.
* Each output record is the winning event with the `deleted` key removed and
  `updated_at` rewritten in UTC as `"YYYY-MM-DDTHH:MM:SSZ"`. All other keys
  are kept as-is.
* `records` is sorted by `id` (plain string order: `"task_10" < "task_2"`).
* **conflicts**: for every group of events with the same `id`, same
  `updated_at` instant and same `version` whose **content differs**, one
  `{"id", "version", "updated_at"}` entry (`updated_at` formatted as above).
  Content means every key except `updated_at`, with a missing `deleted`
  counted as `False`. Identical duplicates are not conflicts. Report the group
  even if a newer version later supersedes it. Sorted by
  `(id, updated_at, version)`.
* Don't mutate the input events.

## Example

```python
records, conflicts = materialize(STREAM)
records[0]   # {"id": "task_2", "version": 2, "updated_at": "2024-05-01T09:30:00Z",
             #  "status": "in_progress", "assignee": "ann_7"}
             # v2 at 09:30Z beats v3 at 09:15Z: time first, version only breaks ties
conflicts    # [{"id": "task_7", "version": 4, "updated_at": "2024-05-02T00:00:00Z"}]
[r["id"] for r in records]   # ["task_2", "task_3", "task_5", "task_7"]   (task_10 was deleted)
```

## Constraints

* Standard library only. Must work on Python 3.10 (`fromisoformat` doesn't take `"Z"` there).
* One pass to pick winners is enough; don't sort the whole stream per id.

<details><summary>Hint 1</summary>

The winner is a `max` over a tuple key: `(instant, version, position)`.
Including the position (from `enumerate`) is what makes "later in the input
wins" explicit instead of depending on how `max` breaks ties (it keeps the
**first** maximum).
</details>

<details><summary>Hint 2</summary>

For conflicts, group events by `(id, instant, version)` in a
`defaultdict(list)` and compare each group's contents. Compare the parsed
instant, never the raw string: `"14:00:00+02:00"` and `"12:00:00Z"` are the
same moment.
</details>

## Follow-up (talk it through)

* Wall-clock `updated_at` across regions can skew. What would you order by
  instead if you could change the producer?
* When do you keep tombstones around instead of dropping the id, and for how long?
* A conflict shows up in production. Do you pick a winner, halt the consumer,
  or quarantine the id? Who gets paged?
