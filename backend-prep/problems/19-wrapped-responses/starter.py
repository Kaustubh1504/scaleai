"""19. Unwrapping inconsistent envelopes

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from typing import Any
import httpx

ENVELOPE_KEYS = ("data", "results", "items")
INNER_KEYS = ("items", "results")
ROLES = {"/v1/annotators": "annotator", "/v1/reviewers": "reviewer", "/v1/leads": "lead"}


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
    raise NotImplementedError


def fetch_everything(client: httpx.Client) -> list[dict]:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import make_api

    for person in fetch_everything(make_api().client()):
        print(person)
    single = fetch_everything(make_api(leads_shape="single").client())
    print("leads when the envelope is a single object:", [p for p in single if p["role"] == "lead"])
