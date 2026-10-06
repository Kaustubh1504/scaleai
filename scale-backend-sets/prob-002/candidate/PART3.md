# Part 3: Priority queue and retry budget (about 20 minutes)

Callers don't want to handle `NoWorkersAvailable` themselves. They want to
hand over work and have the balancer run it in priority order, hold it while
the fleet is down, and give up on tasks that keep failing.

## Contract (keep these signatures)

```python
lb.submit(task) -> None
lb.drain() -> list[DispatchResult]
lb.pending() -> list[Task]
lb.failed   # list[tuple[Task, str]]: (task, reason), oldest first
```

## Queue

* `submit(task)` adds the task to the queue without dispatching it. Raise
  `ValueError` if a task with the same `id` is already pending. The id can be
  used again once that task has left the queue.
* Dispatch order: highest `priority` first. Tasks with equal priority go in
  submission order (FIFO).
* `pending()` returns a new list of the queued tasks, in dispatch order.
  Changing that list does not change the queue.

## `drain()`

Takes tasks from the front of the queue one at a time and dispatches each
with the Part 1 routing rules, until the queue is empty or drain stops (see
below). It returns the `DispatchResult`s of the tasks that succeeded during
this call, in dispatch order.

**Attempt budget.** A task is sent to at most `max_attempts` workers in
total, counted by `task.attempts` across all drains. When a task reaches
`max_attempts` attempts without success, stop trying it even if `ACTIVE`
workers remain.

For each task:

| outcome | what happens | drain then |
|---|---|---|
| a worker succeeds | the task leaves the queue; its result is returned | continues |
| `TaskFailed` | the task leaves the queue and is appended to `lb.failed` as `(task, reason)` | continues |
| the task reached `max_attempts` attempts | the task leaves the queue and is appended to `lb.failed` as `(task, reason)` | continues |
| no `ACTIVE` worker is left and the task still has attempts to spare | the task **stays at the front of the queue** | **stops** |

`reason` is a non-empty string. The same `Task` object that was submitted is
the one stored in `lb.failed`. When drain stops, nothing is lost or reordered:
the task that stopped it, and every task behind it, stay queued in the same
order. Tasks behind it are not tried. The next `drain()` call picks up from
there, and attempts already spent still count.

`drain()` does not call `check_health()` and does not wait for workers to
recover; call it again later. With no tasks queued it returns `[]`.

## Discussion (no code required)

Be ready to talk about:

* A worker times out *after* doing the work, and we fail the task over to
  another worker. What does the caller see, and how would you make that safe?
* Running several balancer instances in front of the same fleet: what state
  do they share, and how?
* Heartbeat timeouts: what happens during a 4-second GC pause on a worker, or
  a network partition between the balancer and half the fleet?
