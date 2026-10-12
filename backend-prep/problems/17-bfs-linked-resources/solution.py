"""17. Crawl linked resources with BFS: reference solution."""

from __future__ import annotations

from collections import deque

import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def collect_teams(client: httpx.Client, root_id: str, max_depth: int | None = None) -> dict:
    seen = {root_id}  # mark when enqueued, so an org is never queued twice
    queue = deque([(root_id, 0)])
    visited = 0
    teams: set[str] = set()
    missing: list[str] = []
    while queue:
        org_id, depth = queue.popleft()
        resp = client.get(f"/v1/orgs/{org_id}")
        if resp.status_code == 404 and depth > 0:
            missing.append(org_id)
            continue
        if not resp.is_success:
            raise ApiError(resp.status_code, f"/v1/orgs/{org_id}", resp.text)
        node = resp.json()
        visited += 1
        teams.update(node["team_ids"])
        if max_depth is None or depth < max_depth:
            for child in node["children"]:
                if child not in seen:
                    seen.add(child)
                    queue.append((child, depth + 1))
    return {"orgs_visited": visited, "team_ids": sorted(teams), "missing_orgs": sorted(missing)}


if __name__ == "__main__":
    from problem_api import make_api

    api = make_api()
    print(collect_teams(api.client(), "org_acme"))
    print("requests:", len(api.log))
    print("depth 1:", collect_teams(make_api().client(), "org_acme", max_depth=1))
