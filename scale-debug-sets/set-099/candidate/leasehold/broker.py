from datetime import timedelta

from .models import Lease, LeaseError, TaskClosed, UnknownTask, UnknownWorker

REJECTION_REASONS = (
    (UnknownTask, "unknown_task"),
    (UnknownWorker, "unknown_worker"),
    (LeaseError, "not_holder"),
    (TaskClosed, "closed"),
)


def fmt(ts):
    return ts.strftime("%H:%M:%S")


# VERIFIED
def is_expired(lease, now):
    return now >= lease.expires_at


# VERIFIED
def pick_next(candidates):
    return min(candidates, key=lambda t: (t.priority, t.created_at, t.id))


class Broker:
    def __init__(self, tasks, workers, lease_seconds):
        self.tasks = tasks
        self.workers = workers
        self.lease_seconds = lease_seconds
        self.leases = []
        self.dispatch = []
        self.expired = []
        self.rejected = []

    def _lease_for(self, task_id):
        return next((lease for lease in self.leases if lease.task_id == task_id), None)

    def _release(self, task, now):
        task.status = "dead" if task.attempts >= task.max_attempts else "pending"
        if task.status == "dead":
            task.finished_at = now

    def reap(self, now):
        for lease in self.leases:
            if is_expired(lease, now):
                self.leases.remove(lease)
                self.expired.append([fmt(now), lease.worker, lease.task_id])
                self._release(self.tasks[lease.task_id], now)

    def _held(self, worker, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            raise UnknownTask(task_id)
        if task.status in ("done", "dead"):
            raise TaskClosed(task_id)
        lease = self._lease_for(task_id)
        if lease is None or lease.worker != worker:
            raise LeaseError(task_id)
        return task, lease

    def claim(self, ev):
        types = self.workers[ev.worker]
        pending = [t for t in self.tasks.values() if t.status == "pending" and t.type in types]
        if not pending:
            self.dispatch.append([fmt(ev.at), ev.worker, None])
            return
        task = pick_next(pending)
        task.status = "leased"
        task.attempts += 1
        task.first_claimed_at = task.first_claimed_at or ev.at
        self.leases.append(Lease(task.id, ev.worker, ev.at + timedelta(seconds=self.lease_seconds[task.type])))
        self.dispatch.append([fmt(ev.at), ev.worker, task.id])

    def heartbeat(self, ev):
        task, lease = self._held(ev.worker, ev.task_id)
        lease.expires_at = ev.at + timedelta(seconds=self.lease_seconds[task.type])

    def ack(self, ev):
        task, lease = self._held(ev.worker, ev.task_id)
        self.leases.remove(lease)
        task.status = "done"
        task.finished_at = ev.at

    def nack(self, ev):
        task, lease = self._held(ev.worker, ev.task_id)
        self.leases.remove(lease)
        self._release(task, ev.at)

    def handle(self, ev):
        self.reap(ev.at)
        try:
            if ev.worker not in self.workers:
                raise UnknownWorker(ev.worker)
            getattr(self, ev.action)(ev)
        except LeaseError as exc:
            reason = next(r for cls, r in REJECTION_REASONS if isinstance(exc, cls))
            self.rejected.append([fmt(ev.at), ev.worker, ev.action, ev.task_id, reason])
