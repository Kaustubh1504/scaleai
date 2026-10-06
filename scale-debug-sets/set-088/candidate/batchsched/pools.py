from collections import Counter


class PoolTable:
    """Tracks which active worker is running which job."""

    def __init__(self, workers):
        self.workers = sorted((w for w in workers if w.active), key=lambda w: w.id)
        self.busy = {}

    def free_worker(self, pool):
        for worker in self.workers:
            if worker.pool == pool and worker.id not in self.busy:
                return worker
        return None

    def assign(self, worker, job_id):
        self.busy[worker.id] = job_id

    def release(self, worker_id):
        self.busy.pop(worker_id, None)


def pool_names(workers):
    return sorted({w.pool for w in workers})


def capacity(workers):
    """pool -> number of workers that can take jobs."""
    return Counter(w.pool for w in workers)
