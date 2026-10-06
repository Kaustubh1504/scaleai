from .loader import fmt_ms
from .models import Lease, Worker

LEASE_MS = 60_000


# VERIFIED
def pick_next(tasks):
    pending = [t for t in tasks if t.status == "pending"]
    if not pending:
        return None
    return min(pending, key=lambda t: (t.priority, t.enqueued_ms, t.task_id))


class Broker:
    def __init__(self, tasks):
        self.tasks = {t.task_id: t for t in tasks}
        self.leases = {}
        self.workers = {}
        self.dispatch = []
        self.heartbeats = []
        self.rejected_acks = []

    def worker(self, worker_id):
        if worker_id not in self.workers:
            self.workers[worker_id] = Worker(worker_id)
        return self.workers[worker_id]

    def reap(self, now_ms):
        for task_id, lease in list(self.leases.items()):
            if now_ms > lease.deadline_ms:
                del self.leases[task_id]
                task = self.tasks[task_id]
                task.status = "dead" if task.attempts >= task.max_attempts else "pending"

    def holds(self, event):
        lease = self.leases.get(event.task_id)
        return lease is not None and lease.worker_id == event.worker_id

    def handle(self, event):
        self.reap(event.ts_ms)
        worker = self.worker(event.worker_id)
        stamp = fmt_ms(event.ts_ms)
        if event.action == "lease":
            task = pick_next(self.tasks.values())
            if task is None:
                self.dispatch.append([stamp, worker.worker_id, None])
                return
            task.attempts += 1
            task.status = "leased"
            if task.first_leased_ms is None:
                task.first_leased_ms = event.ts_ms
            self.leases[task.task_id] = Lease(task.task_id, worker.worker_id, event.ts_ms + LEASE_MS)
            self.dispatch.append([stamp, worker.worker_id, task.task_id])
        elif event.action == "heartbeat":
            ok = self.holds(event)
            if ok:
                self.leases[event.task_id].deadline_ms = event.ts_ms + LEASE_MS
            self.heartbeats.append([stamp, worker.worker_id, event.task_id, "ok" if ok else "rejected"])
        elif event.action == "ack":
            if self.holds(event):
                del self.leases[event.task_id]
                self.tasks[event.task_id].status = "done"
                worker.record(event.task_id)
            else:
                self.rejected_acks.append([stamp, worker.worker_id, event.task_id])

    def replay(self, events, end_ms):
        for event in events:
            self.handle(event)
        self.reap(end_ms)
        return self
