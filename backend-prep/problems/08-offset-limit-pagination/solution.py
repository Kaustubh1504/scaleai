"""08. Offset/limit pagination with a lying total: reference solution."""

from __future__ import annotations

import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def fetch_all_annotations(client: httpx.Client, api_key: str, limit: int = 50) -> list[dict]:
    out = []
    while True:
        resp = client.get("/v1/annotations", params={"offset": len(out), "limit": limit},
                          headers={"X-API-Key": api_key})
        if not resp.is_success:
            raise ApiError(resp.status_code, "/v1/annotations", resp.text)
        body = resp.json()
        out.extend(body["items"])
        # Stop on the server's reported limit, not ours; never trust `total`.
        if not body["items"] or len(body["items"]) < body["limit"]:
            return out


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    api = make_api(n_annotations=130, reported_total=90)
    annotations = fetch_all_annotations(api.client(), API_KEY, limit=100)
    print(len(annotations), "annotations; offsets:", [c.params["offset"] for c in api.log])
