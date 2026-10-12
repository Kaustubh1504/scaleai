"""17. Crawl linked resources with BFS

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import deque
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def fetch_org(client: httpx.Client, org_id: str) -> dict | None:
    """The org, or None on 404. Other errors raise."""
    path = f"/v1/orgs/{org_id}"
    resp = client.get(path)
    if resp.status_code == 404:
        return None
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text[:200])
    return resp.json()


def collect_teams(client: httpx.Client, root_id: str, max_depth: int | None = None) -> dict:
    root = fetch_org(client, root_id)
    if root is None:
        raise ApiError(404, f"/v1/orgs/{root_id}", "root org not found")

    seen = {root_id}            # mark when *enqueued*, so duplicates never get queued twice
    queue = deque([(root, 0)])
    visited = 0
    teams: set[str] = set()
    missing: list[str] = []
    while queue:
        node, depth = queue.popleft()
        visited += 1
        teams.update(node["team_ids"])
        if max_depth is not None and depth >= max_depth:
            continue
        for child_id in node["children"]:
            if child_id in seen:
                continue
            seen.add(child_id)
            child = fetch_org(client, child_id)
            if child is None:
                missing.append(child_id)
            else:
                queue.append((child, depth + 1))

    return {"orgs_visited": visited, "team_ids": sorted(teams), "missing_orgs": sorted(missing)}



if __name__ == "__main__":
    from problem_api import make_api

    api = make_api()
    print(collect_teams(api.client(), "org_acme"))
    print("requests:", len(api.log))
    print("depth 1:", collect_teams(make_api().client(), "org_acme", max_depth=1))
