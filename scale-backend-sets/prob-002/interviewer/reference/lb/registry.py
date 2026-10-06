"""The set of workers the balancer may route to."""

from __future__ import annotations

from typing import Iterator

from lb.models import Worker


class WorkerRegistry:
    """Workers keyed by id, iterated in registration order.

    A worker that is unregistered and registered again goes to the end.
    """

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}

    def register(self, worker: Worker) -> None:
        if worker.worker_id in self._workers:
            raise ValueError(f"worker {worker.worker_id!r} is already registered")
        self._workers[worker.worker_id] = worker

    def unregister(self, worker_id: str) -> Worker:
        try:
            return self._workers.pop(worker_id)
        except KeyError:
            raise KeyError(f"unknown worker {worker_id!r}") from None

    def get(self, worker_id: str) -> Worker | None:
        return self._workers.get(worker_id)

    def ids(self) -> list[str]:
        return list(self._workers)

    def __contains__(self, worker_id: object) -> bool:
        return worker_id in self._workers

    def __iter__(self) -> Iterator[Worker]:
        # A copy, so callers may register/unregister while iterating.
        return iter(list(self._workers.values()))

    def __len__(self) -> int:
        return len(self._workers)
