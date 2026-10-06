"""The set of workers the balancer may route to."""

from __future__ import annotations

from typing import Iterator

from lb.models import Worker


class WorkerRegistry:
    """Workers keyed by id, iterated in registration order."""

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}

    def register(self, worker: Worker) -> None:
        # Registering an id again replaces the old worker object.
        self._workers[worker.worker_id] = worker

    def unregister(self, worker_id: str) -> None:
        self._workers.pop(worker_id, None)

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
