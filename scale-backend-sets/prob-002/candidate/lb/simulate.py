"""Demo: route a small workload across three local workers.

    python -m lb.simulate [path/to/tasks.jsonl]

Each line of the workload file is a JSON object: {"id": str, "priority": int
(optional, default 0), "payload": any (optional, default {"id": <id>})}.
Lines that do not match are skipped with a warning.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from lb.balancer import LoadBalancer
from lb.models import Task
from mock_services.clock import RealClock
from mock_services.workers import MockWorker, WorkerError, default_handler

DEFAULT_TASKS = Path(__file__).resolve().parent.parent / "data" / "tasks.jsonl"

log = logging.getLogger("lb.simulate")


def _parse_task(line: str) -> Task:
    row = json.loads(line)  # json.JSONDecodeError is a ValueError
    if not isinstance(row, dict):
        raise ValueError("line is not a JSON object")
    task_id, priority = row.get("id"), row.get("priority", 0)
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("id must be a non-empty string")
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("priority must be an integer")
    return Task(id=task_id, priority=priority, payload=row.get("payload", {"id": task_id}))


def load_tasks(path: Path) -> list[Task]:
    tasks = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            tasks.append(_parse_task(line))
        except ValueError as exc:
            log.warning("%s:%d skipped: %s", path.name, lineno, exc)
    return tasks


def handler(worker_id: str, payload: Any) -> Any:
    """What the demo workers do with a task: payloads marked "poison" blow up."""
    if isinstance(payload, dict) and payload.get("poison"):
        raise ValueError("cannot process a poison payload")
    return default_handler(worker_id, payload)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    path = Path(argv[0]) if argv else DEFAULT_TASKS
    clock = RealClock()
    balancer = LoadBalancer(clock, task_timeout_s=0.5)
    for i in (1, 2, 3):
        balancer.add_worker(MockWorker(f"w{i}", capacity=2, latency_s=0.01, clock=clock, handler=handler))

    for task in load_tasks(path):
        try:
            result = balancer.dispatch(task)
        except WorkerError as exc:
            print(f"{task.id:<12} !! {exc}")
            continue
        print(f"{task.id:<12} -> {result.worker_id} (attempts={result.attempts})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
