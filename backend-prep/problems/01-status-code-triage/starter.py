"""01. Status code triage

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from dataclasses import dataclass

ACTIONS = {"ok", "fix_request", "reauthenticate", "forbidden", "not_found",
           "conflict", "fix_payload", "back_off", "retry", "give_up"}


@dataclass(frozen=True)
class Triage:
    blame: str       # "none" | "client" | "server"
    retryable: bool
    action: str      # one of ACTIONS


IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


def triage(method: str, status: int, idempotency_key: bool = False) -> Triage:
    raise NotImplementedError


if __name__ == "__main__":
    cases = [
        ("GET", 200, False), ("GET", 503, False), ("POST", 503, False), ("POST", 503, True),
        ("post", 429, False), ("DELETE", 418, False), ("GET", 401, False),
    ]
    for method, status, key in cases:
        print(f"{method:<7} {status} key={key!s:<5} ->", triage(method, status, idempotency_key=key))
