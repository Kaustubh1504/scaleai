"""06. Fix the broken API script. This is the teammate's script: it has three bugs.

Usage: assign the given tasks to active annotators, round-robin, in id order.
"""

from __future__ import annotations

import httpx

DEFAULT_HEADERS = {"Accept": "application/json", "User-Agent": "ops-assign/1.3"}


def auth_headers(token: str) -> dict[str, str]:
    return {**DEFAULT_HEADERS, "Authorization": f"Bearer {token}"}


def list_annotators(client: httpx.Client, token: str, status: str | None = None,
                    page_size: int = 25) -> list[dict]:
    """Every annotator (optionally only those with `status`), in API order, across all pages."""
    annotators: list[dict] = []
    page = 1
    while True:
        params: dict[str, str | int] = {"page": page, "per_page": page_size}
        if status is not None:
            params["status"] = status
        resp = client.get("/v1/annotators", params=params, headers=auth_headers(token))
        resp.raise_for_status()
        body = resp.json()
        print(body)
        annotators.extend(body["data"])
        if page >= body["total_pages"]:
            return annotators
        page += 1


def assign_task(client: httpx.Client, token: str, task_id: str, annotator_id: str) -> dict:
    """Assign one task; returns the created assignment."""
    resp = client.post(f"/v1/tasks/{task_id}/assignments",
                       json={"annotator_id": annotator_id},
                       headers=auth_headers(token))
    resp.raise_for_status()
    return resp.json()


def assign_round_robin(client: httpx.Client, token: str, task_ids: list[str]) -> list[dict]:
    """Assign task_ids[i] to the (i mod n)-th active annotator. ValueError if nobody is active."""
    active = list_annotators(client, token, status="active")
    if not active:
        raise ValueError("no active annotators")
    return [assign_task(client, token, task_id, active[i % len(active)]["id"])
            for i, task_id in enumerate(task_ids)]


if __name__ == "__main__":
    # "Run" executes this block: it runs the script the way the teammate did.
    from problem_api import TOKEN, make_api

    api = make_api()
    client = api.client()
    print("annotators:", len(list_annotators(client, TOKEN, page_size=10)))
    for a in assign_round_robin(client, TOKEN, ["task_001", "task_002", "task_003"]):
        print(a)
