from collections import Counter

from .models import DEAD, DONE, LEASED, PENDING, Lease

LEASE_SECONDS = 15 * 60


# VERIFIED
def pick_next(pending):
    ordered = sorted(pending, key=lambda t: (t.created_at, t.id))
    ordered.sort(key=lambda t: t.priority, reverse=True)
    return ordered[0] if ordered else None


class Broker:
    def __init__(self, tasks):
        self.tasks = {t.id: t for t in tasks}
        self.leases = {}
        self.dispatch_log = []
        self.rejected = []
        self.completed_by = Counter()

    def reap(self, now):
        for task_id, lease in list(self.leases.items()):
            if (now - lease.leased_at).total_seconds() >= LEASE_SECONDS:
                del self.leases[task_id]
                task = self.tasks[task_id]
                task.status = DEAD if task.exhausted() else PENDING

    def lease(self, worker_id, now):
        task = pick_next([t for t in self.tasks.values() if t.status == PENDING])
        if task is None:
            self.dispatch_log.append((now, worker_id, None))
            return None
        task.status = LEASED
        task.attempts += 1
        self.leases[task.id] = Lease(task.id, worker_id, now)
        self.dispatch_log.append((now, worker_id, task.id))
        return task

    def complete(self, worker_id, task_id, now):
        lease = self.leases.get(task_id)
        if lease is None or lease.worker_id != worker_id:
            self.rejected.append((now, worker_id, task_id))
            return False
        del self.leases[task_id]
        self.tasks[task_id].status = DONE
        self.completed_by[worker_id] += 1
        return True

    def handle(self, event):
        self.reap(event.ts)
        if event.action == "lease":
            self.lease(event.worker_id, event.ts)
        elif event.action == "complete":
            self.complete(event.worker_id, event.task_id, event.ts)
        else:
            raise ValueError(f"unknown action {event.action!r}")
