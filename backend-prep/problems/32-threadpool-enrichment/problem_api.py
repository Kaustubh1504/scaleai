"""Mock Tasks API for problem 32. Tests and your __main__ block both use make_api().

Each request really sleeps (about ``latency_s`` on average, between 0.4x and
1.6x depending on the task id), so 200 serial requests at 0.02 s take ~4 s,
and responses come back in a different order than they were sent.
"""

from __future__ import annotations

import time

from kit import MockAPI, error_response

PROJECTS = ("proj_alpha", "proj_beta", "proj_gamma")
STATUSES = ("queued", "in_progress", "completed", "reviewed")


def task_id(i: int) -> str:
    return f"task_{i:04d}"


def make_task(i: int) -> dict:
    return {
        "id": task_id(i),
        "project_id": PROJECTS[i % 3],
        "status": STATUSES[i % 4],
        "annotator_id": f"ann_{(i * 7) % 13:02d}",
        "label_count": (i * 5) % 9,
    }


def make_api(n_tasks: int = 200, *, latency_s: float = 0.02) -> MockAPI:
    """
    n_tasks   : tasks task_0001 .. task_<n_tasks> exist; any other id is a 404.
    latency_s : average real time each request takes.
    """
    api = MockAPI()
    tasks = {task_id(i): make_task(i) for i in range(1, n_tasks + 1)}
    api.tasks = tasks

    @api.route("GET", "/v1/tasks/{tid}")
    def get_task(req, tid):
        # Sleeping inside the handler counts toward api.in_flight / api.max_in_flight.
        n = int(tid.rsplit("_", 1)[-1]) if tid.rsplit("_", 1)[-1].isdigit() else 0
        time.sleep(latency_s * (1 + (n * 7) % 4) / 2.5)
        if tid not in tasks:
            return error_response(404, f"task {tid} not found")
        return dict(tasks[tid])

    return api
