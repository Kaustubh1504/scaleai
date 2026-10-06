# Part 2: Redundancy and consensus (about 20 minutes)

One annotator's answer is not enough for training data. Each task should be
labelled by several **different** annotators, and the service decides the
final label by majority vote.

`create_app(..., redundancy=N)` sets how many submissions every task needs
(the tests use `redundancy=3`). Everything from Part 1 still holds unless
this page changes it.

## Claiming

Several annotators can hold live leases on the same task at the same time.
For annotator `A`, a task is **claimable** when all of these are true:

* it is not final (`submitted`, `completed` or `disputed`);
* `A` has never submitted a label for it;
* `submissions + live leases < redundancy` for that task (each live lease
  holds one of the remaining slots; an expired lease frees its slot).

`POST /tasks/claim` gives the caller the oldest claimable task by creation
order. As in Part 1, a caller who already holds a live lease (on any task) gets
that task back, unchanged. An annotator who submitted a task can **never**
claim it again.

## States

| state | meaning |
|---|---|
| `pending` | fewer than `redundancy` submissions and no live leases |
| `leased` | fewer than `redundancy` submissions and at least one live lease |
| `completed` | `redundancy` submissions and a majority label (final) |
| `disputed` | `redundancy` submissions and no majority label (final) |

With `redundancy=1` nothing changes from Part 1: the task ends in `submitted`.

## Consensus

When a task receives its `redundancy`-th submission:

* let `votes` be the count of the most common label;
* if `votes > redundancy / 2` (a strict majority; with 3 that means at least 2)
  the task becomes `completed` with `consensus_label` = that label;
* otherwise it becomes `disputed` with `consensus_label = null`;
* in both cases `agreement = round(votes / redundancy, 2)` (e.g. `0.67`, `0.33`, `1.0`).

## The task object

Add two fields to every task object:

```json
{"...": "...", "state": "completed", "consensus_label": "positive", "agreement": 0.67,
 "submissions": [{"annotator_id": "alice", "label": "positive", "submitted_at": 1700000010.0},
                 {"annotator_id": "bob",   "label": "negative", "submitted_at": 1700000011.0},
                 {"annotator_id": "carol", "label": "positive", "submitted_at": 1700000012.0}]}
```

`consensus_label` and `agreement` are `null` until the task is `completed` or
`disputed` (and always `null` with `redundancy=1`). `submissions` lists every
submission in the order they were made. `GET /tasks?state=completed` (and
`disputed`) work like the other states.

## Errors

Submitting to a `completed` or `disputed` task, or submitting without a live
lease, is **409**, as in Part 1.

Write tests for the new rules.
