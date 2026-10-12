"""32. Thread pool enrichment: reference solution."""

from concurrent.futures import ThreadPoolExecutor

import httpx


class ApiError(Exception):
    def __init__(self, status: int, task_id: str, message: str = ""):
        super().__init__(f"{status} for {task_id}: {message}")
        self.status = status
        self.task_id = task_id


def enrich(client: httpx.Client, task_ids: list[str], max_workers: int = 8) -> list[dict]:
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")

    def fetch(tid: str) -> dict:
        resp = client.get(f"/v1/tasks/{tid}")
        if not resp.is_success:
            raise ApiError(resp.status_code, tid, resp.text)
        return resp.json()

    unique = list(dict.fromkeys(task_ids))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        by_id = dict(zip(unique, pool.map(fetch, unique)))
    return [by_id[tid] for tid in task_ids]


if __name__ == "__main__":
    from problem_api import make_api

    api = make_api(n_tasks=200)
    rows = enrich(api.client(), [f"task_{i:04d}" for i in range(1, 201)])
    print(len(rows), "tasks, max in flight =", api.max_in_flight)
