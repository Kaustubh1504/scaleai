"""Mock Tasks API for problem 12. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from kit import MockAPI, error_response


def make_tasks(n: int) -> dict[str, dict]:
    kinds = ("bbox", "transcribe", "classify")
    return {f"task_{i:03d}": {"id": f"task_{i:03d}", "kind": kinds[i % 3], "priority": i % 5}
            for i in range(1, n + 1)}


def make_api(n_tasks: int = 20, *, clock=None) -> MockAPI:
    """
    GET  /v1/tasks/{task_id}         -> the task, or 404
    POST /v1/tasks/{task_id}/labels  {"label": str} -> 201 {"id", "task_id", "label"}; 422 without a label

    Inject faults with api.script("GET /v1/tasks/task_001", [503, "timeout", "malformed", ...]).
    """
    api = MockAPI(clock=clock)
    tasks = make_tasks(n_tasks)
    labels: list[dict] = []
    api.tasks = tasks
    api.labels = labels

    @api.route("GET", "/v1/tasks/{task_id}")
    def get_task(req, task_id):
        if task_id not in tasks:
            return error_response(404, f"task {task_id} not found")
        return tasks[task_id]

    @api.route("POST", "/v1/tasks/{task_id}/labels")
    def add_label(req, task_id):
        if task_id not in tasks:
            return error_response(404, f"task {task_id} not found")
        try:
            body = req.json() or {}
        except ValueError:
            return error_response(400, "body must be JSON")
        if not isinstance(body.get("label"), str) or not body["label"]:
            return error_response(422, "label is required")
        label = {"id": f"lbl_{len(labels) + 1:04d}", "task_id": task_id, "label": body["label"]}
        labels.append(label)
        return 201, label

    return api
