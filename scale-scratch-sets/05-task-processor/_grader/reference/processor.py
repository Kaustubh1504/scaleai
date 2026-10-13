"""Reference solution for 05-task-processor. Hidden from the candidate."""

from __future__ import annotations

import heapq
from collections import defaultdict


class TaskProcessor:
    def __init__(self) -> None:
        # Ready heap entries: (deadline, add_seq, version, task_id).
        # add_seq is fixed at add_task time, so ties always use the original add order.
        # version is unique per push, so tuple comparison never reaches task_id.
        self._heap: list[tuple[float, int, int, str]] = []
        self._version_counter = 0

        # Pending (added, not consumed) tasks.
        self._deadline: dict[str, float] = {}
        self._seq: dict[str, int] = {}
        self._version: dict[str, int] = {}  # latest live heap version (ready tasks only)
        self._unmet: dict[str, int] = {}  # distinct prerequisites not yet consumed

        self._parents: defaultdict[str, list[str]] = defaultdict(list)  # subtask -> waiting parents
        self._consumed: set[str] = set()
        self._next_seq = 0

    # ---- helpers -------------------------------------------------------
    def _push(self, task_id: str) -> None:
        self._version_counter += 1
        v = self._version_counter
        self._version[task_id] = v
        heapq.heappush(self._heap, (self._deadline[task_id], self._seq[task_id], v, task_id))

    # ---- Part 1 / 2 ----------------------------------------------------
    def add_task(self, task_id: str, deadline: float, subtasks: list[str] | None = None) -> None:
        if task_id in self._deadline or task_id in self._consumed:
            raise ValueError(f"duplicate task_id: {task_id!r}")

        unmet = {s for s in (subtasks or ()) if s not in self._consumed}

        self._deadline[task_id] = deadline
        self._seq[task_id] = self._next_seq
        self._next_seq += 1
        self._unmet[task_id] = len(unmet)
        for s in unmet:
            self._parents[s].append(task_id)
        if not unmet:
            self._push(task_id)

    def consume_task(self) -> str | None:
        heap = self._heap
        while heap:
            _, _, v, tid = heapq.heappop(heap)
            if self._version.get(tid) != v:
                continue  # stale (updated since, or already consumed)
            del self._version[tid]
            del self._deadline[tid]
            del self._seq[tid]
            del self._unmet[tid]
            self._consumed.add(tid)
            for parent in self._parents.pop(tid, ()):
                self._unmet[parent] -= 1
                if self._unmet[parent] == 0:
                    self._push(parent)
            return tid
        return None

    # ---- Part 3 --------------------------------------------------------
    def update_deadline(self, task_id: str, new_deadline: float) -> None:
        if task_id not in self._deadline:
            raise KeyError(task_id)
        self._deadline[task_id] = new_deadline
        if self._unmet[task_id] == 0:
            self._push(task_id)  # old entry becomes stale (lazy deletion)

    def __len__(self) -> int:
        return len(self._deadline)
