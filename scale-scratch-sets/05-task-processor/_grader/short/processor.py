"""Short reference solution for 05-task-processor."""

import heapq
import itertools
from collections import defaultdict


class TaskProcessor:
    def __init__(self):
        self.heap = []  # (deadline, add_seq, task_id) -- ready tasks only
        self.deadline = {}  # pending task -> current deadline
        self.seq = {}  # pending task -> add order (never changes)
        self.unmet = {}  # pending task -> count of distinct unconsumed subtasks
        self.parents = defaultdict(list)  # subtask -> parents waiting on it
        self.consumed = set()
        self.counter = itertools.count()

    def _push(self, tid):
        heapq.heappush(self.heap, (self.deadline[tid], self.seq[tid], tid))

    def add_task(self, task_id, deadline, subtasks=None):
        if task_id in self.deadline or task_id in self.consumed:
            raise ValueError(task_id)
        unmet = set(subtasks or ()) - self.consumed
        self.deadline[task_id] = deadline
        self.seq[task_id] = next(self.counter)
        self.unmet[task_id] = len(unmet)
        for s in unmet:
            self.parents[s].append(task_id)
        if not unmet:
            self._push(task_id)

    def consume_task(self):
        while self.heap:
            d, _, tid = heapq.heappop(self.heap)
            # Lazy deletion: skip entries for consumed tasks or outdated deadlines.
            # (A repeated deadline can leave two live-looking entries; the second
            # is skipped because the task is consumed by then.)
            if self.deadline.get(tid) != d:
                continue
            del self.deadline[tid], self.seq[tid], self.unmet[tid]
            self.consumed.add(tid)
            for parent in self.parents.pop(tid, ()):
                self.unmet[parent] -= 1
                if self.unmet[parent] == 0:
                    self._push(parent)
            return tid
        return None

    def update_deadline(self, task_id, new_deadline):
        if task_id not in self.deadline:
            raise KeyError(task_id)
        self.deadline[task_id] = new_deadline
        if self.unmet[task_id] == 0:
            self._push(task_id)  # old entry stays in the heap and goes stale

    def __len__(self):
        return len(self.deadline)
