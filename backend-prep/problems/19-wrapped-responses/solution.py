"""19. Unwrapping inconsistent envelopes: reference solution."""

from __future__ import annotations

from typing import Any

import httpx


class UnexpectedShape(Exception):
    def __init__(self, keys: list[str]):
        super().__init__(f"unrecognised response envelope; top-level keys: {keys}")
        self.keys = keys


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def unwrap(body: Any) -> list[dict]:
    if isinstance(body, list):
        return body
    if not isinstance(body, dict):
        raise UnexpectedShape([])
    key = next((k for k in ("data", "results", "items") if k in body), None)
    if key is None:
        raise UnexpectedShape(sorted(body))
    value = body[key]
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for inner in ("items", "results"):
            if isinstance(value.get(inner), list):
                return value[inner]
        return [value]
    raise UnexpectedShape(sorted(body))


def fetch_everything(client: httpx.Client) -> list[dict]:
    people = []
    for role in ("annotator", "reviewer", "lead"):
        path = f"/v1/{role}s"
        resp = client.get(path)
        if not resp.is_success:
            raise ApiError(resp.status_code, path, resp.text)
        people += [{"id": r["id"], "name": r["name"], "role": role} for r in unwrap(resp.json())]
    return sorted(people, key=lambda p: p["id"])


if __name__ == "__main__":
    from problem_api import make_api

    for person in fetch_everything(make_api().client()):
        print(person)
    single = fetch_everything(make_api(leads_shape="single").client())
    print("single-object leads:", [p for p in single if p["role"] == "lead"])
