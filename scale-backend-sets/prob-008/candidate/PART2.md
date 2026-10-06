# Part 2: The real data is messy (about 20 minutes)

The production API does not always send canonical values (see "Data quality"
in `API.md` and the examples in `data/recorded/`). Run your code against
`make_api()` (messy by default) and make it correct there. Finance also needs
two new things in the report.

## Interpreting wire values

Apply these rules to every field your calculation reads. Each wire form has
exactly one meaning:

| field(s) | forms you will see | meaning |
|---|---|---|
| `submitted_at`, review `created_at` (any timestamp) | ISO-8601 with `Z`; with an offset such as `+00:00`; with no offset; a JSON number | no offset means UTC. A number is Unix epoch time: **seconds**, or **milliseconds** when the value is `>= 10**11` |
| `reward_cents` | an integer; a string of digits (`"12"`); `null`; key missing | a digit string is that integer. `null` or missing means the reward is **unknown** (below) |
| `verdict`, `answer.label`, `gold_label` | any casing, surrounding whitespace (`" APPROVED "`) | compare after trimming whitespace and ignoring case |
| `is_active`, `is_gold` (any boolean) | `true`/`false`, `"true"`/`"false"`, `1`/`0` | the obvious boolean |

A value that matches none of these forms should stop the run with an error that
names the record. It must never be silently treated as zero.

## Unknown rewards

An approved submission on a task whose reward is unknown still counts as
`approved`, but earns nothing. Every such task is listed in a new top-level key
`unknown_reward_task_ids`: the ids of tasks with an unknown reward that have
**at least one approved submission in the period**, sorted, without duplicates
(`[]` if none). Finance resolves these by hand.

## Annotators on hold

An annotator whose `is_active` is false is on hold: their row is still shown,
with their earnings computed as usual, but they must not be paid yet.

* Every row gets `"on_hold": true | false`.
* `totals.earnings_cents` stays the sum over all rows.
* New `totals.payable_cents`: the sum of `earnings_cents` over rows with `on_hold: false`.

```json
{
  "period": "2024-04-01T00:00:00Z/2024-04-15T00:00:00Z",
  "annotators": [
    {"annotator_id": "ann_001", "handle": "annotator001", "approved": 2, "rejected": 1, "pending": 2,
     "earnings_cents": 13, "on_hold": false}
  ],
  "unknown_reward_task_ids": ["tsk_0009", "tsk_0204"],
  "totals": {"annotators": 29, "approved": 82, "rejected": 23, "pending": 78,
             "earnings_cents": 1253, "payable_cents": 1021}
}
```

Write tests for each rule, using `api.rendered("submissions")` etc. to see
what the wire looks like, and `api.insert(...)` for records with known outcomes.
