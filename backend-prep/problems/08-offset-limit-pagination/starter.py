"""08. Offset/limit pagination with a lying total

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def fetch_all_annotations(client: httpx.Client, api_key: str, limit: int = 50) -> list[dict]:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    api = make_api(n_annotations=130, reported_total=90)
    annotations = fetch_all_annotations(api.client(), API_KEY, limit=100)
    print(len(annotations), "annotations; offsets:", [c.params["offset"] for c in api.log])
