from .models import LeaseError, LeaseExpired, NotOwner

# most specific first
REJECTION_CODES = [(LeaseError, "invalid"), (LeaseExpired, "expired"), (NotOwner, "not_owner")]


def rejection_code(exc):
    for cls, code in REJECTION_CODES:
        if isinstance(exc, cls):
            return code
    raise exc


# VERIFIED
def lease_expired(task, now_ms):
    return task.state == "leased" and now_ms >= task.expires_ms


# VERIFIED
def next_task(tasks, now_ms):
    ready = [t for t in tasks.values() if t.state == "ready" and t.enqueued_ms <= now_ms]
    return min(ready, key=lambda t: (t.priority, t.enqueued_ms, t.id), default=None)


class Broker:
    def __init__(self, tasks, lease_ms):
        self.tasks = tasks
        self.lease_ms = lease_ms
        self.holding = {}

    def _release(self, task):
        self.holding.pop(task.owner, None)
        task.past_owners.append(task.owner)
        task.owner = task.expires_ms = None
        task.state = "dead" if task.attempts >= task.max_attempts else "ready"

    def reap(self, now_ms):
        for task in self.tasks.values():
            if lease_expired(task, now_ms):
                self._release(task)

    def poll(self, worker_id, now_ms):
        if worker_id in self.holding:
            return None
        task = next_task(self.tasks, now_ms)
        if task is None:
            return None
        task.state, task.owner = "leased", worker_id
        task.expires_ms = now_ms + self.lease_ms
        task.attempts += 1
        if task.first_claim_ms is None:
            task.first_claim_ms = now_ms
        self.holding[worker_id] = task.id
        return task.id

    def _owned(self, worker_id, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            raise LeaseError(task_id)
        if task.owner == worker_id:
            return task
        if worker_id in task.past_owners:
            raise LeaseExpired(task_id)
        raise NotOwner(task_id)

    def heartbeat(self, worker_id, task_id, now_ms):
        self._owned(worker_id, task_id).expires_ms = now_ms + self.lease_ms

    def ack(self, worker_id, task_id):
        task = self._owned(worker_id, task_id)
        self.holding.pop(worker_id, None)
        task.state, task.owner, task.expires_ms = "done", None, None
        task.completed_by = worker_id

    def fail(self, worker_id, task_id):
        self._release(self._owned(worker_id, task_id))
