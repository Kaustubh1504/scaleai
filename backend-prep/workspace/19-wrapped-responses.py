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
    if isinstance(body, list):              # NEW: a bare list is already the records
        return list(body)
    if not isinstance(body, dict):          # NEW: None, a string, a number...
        raise UnexpectedShape([])

    v = None
    found = False                           # NEW: remember whether a key was found
    for k in ENVELOPE_KEYS:                 # CHANGED: loop over YOUR keys, not body's
        if k in body:
            v = body[k]
            found = True
            break
    if not found:                           # NEW: no envelope key means raise, not []
        raise UnexpectedShape(sorted(body))

    if v is None:                           # CHANGED: was `if not v`, and moved up
        return []
    if isinstance(v, list): return v
    if isinstance(v, dict):
        for k in INNER_KEYS:                # CHANGED: loop over YOUR keys
            if isinstance(v.get(k), list):  # CHANGED: .get() is safe if k is missing
                return v[k]
        return [v]                          # CHANGED: moved out of the loop

    raise UnexpectedShape(sorted(body))
    
    


def fetch_everything(client: httpx.Client) -> list[dict]:
    people = []
    for path, role in ROLES.items():
        resp = client.get(path)
        if not resp.is_success:
            raise ApiError(resp.status_code, path, resp.text[:200])
        for rec in unwrap(resp.json()):
            people.append({"id": rec["id"], "name": rec["name"], "role": role})
    return sorted(people, key=lambda p: p["id"])

if __name__ == "__main__":
    from problem_api import make_api

    for person in fetch_everything(make_api().client()):
        print(person)
    single = fetch_everything(make_api(leads_shape="single").client())
    print("leads when the envelope is a single object:", [p for p in single if p["role"] == "lead"])
