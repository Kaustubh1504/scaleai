from collections import Counter
from datetime import timedelta

from .models import DEAD, DONE, LEASED, PENDING, Lease

LEASE_LENGTH = timedelta(minutes=10)
MAX_EXTENSIONS = 2


# VERIFIED
def next_pending(tasks, queue):
    pending = [t for t in tasks if t.queue == queue and t.status == PENDING]
    if not pending:
        return None
    return min(pending, key=lambda t: (t.priority, t.created_at, t.id))


class Ledger:
    def __init__(self, tasks):
        self.tasks = {t.id: t for t in tasks}
        self.active = []  # leases in the order they were taken
        self.claims = []
        self.rejected = []
        self.acks = Counter()
        self.lost = Counter()

    def reap(self, now):
        for lease in list(self.active):
            if lease.expires_at <= now:
                self.active.remove(lease)
                self._expire(lease)

    def _expire(self, lease):
        task = lease.task
        task.status = DEAD if task.attempts >= task.max_attempts else PENDING
        self.lost[lease.worker] += 1

    def holding(self, task_id, worker):
        for lease in self.active:
            if lease.task.id == task_id and lease.worker == worker:
                return lease
        return None

    def handle(self, event):
        self.reap(event.at)
        if event.action == "claim":
            self.claim(event)
        elif event.action == "heartbeat":
            self.heartbeat(event)
        elif event.action == "ack":
            self.ack(event)
        else:
            self.reject(event)

    def claim(self, event):
        task = next_pending(self.tasks.values(), event.queue)
        self.claims.append((event.at, event.worker, event.queue, task.id if task else None))
        if task is None:
            return
        task.status = LEASED
        task.attempts += 1
        self.active.append(Lease(task, event.worker, event.at, event.at + LEASE_LENGTH))

    def heartbeat(self, event):
        lease = self.holding(event.task_id, event.worker)
        # each lease may be extended up to MAX_EXTENSIONS times
        if lease is None or lease.extensions >= MAX_EXTENSIONS:
            self.reject(event)
            return
        lease.expires_at = event.at + LEASE_LENGTH
        lease.extensions += 1
        lease.task.extensions += 1

    def ack(self, event):
        lease = self.holding(event.task_id, event.worker)
        if lease is None:
            self.reject(event)
            return
        self.active.remove(lease)
        lease.task.status = DONE
        self.acks[event.worker] += 1

    def reject(self, event):
        self.rejected.append((event.at, event.action, event.worker, event.task_id))
