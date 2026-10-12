"""32. Thread pool enrichment

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import httpx


class ApiError(Exception):
    def __init__(self, status: int, task_id: str, message: str = ""):
        super().__init__(f"{status} for {task_id}: {message}")
        self.status = status
        self.task_id = task_id


def fetch_task(client: httpx.Client, task_id: str) -> dict:
    raise NotImplementedError


def enrich(client: httpx.Client, task_ids: list[str], max_workers: int = 8) -> list[dict]:
    raise NotImplementedError


if __name__ == "__main__":
    import time

    from problem_api import make_api

    api = make_api(n_tasks=200)
    ids = [f"task_{i:04d}" for i in range(1, 201)]
    started = time.perf_counter()
    rows = enrich(api.client(), ids, max_workers=8)
    print(f"{len(rows)} tasks in {time.perf_counter() - started:.2f}s, max in flight = {api.max_in_flight}")
    print(rows[0])
