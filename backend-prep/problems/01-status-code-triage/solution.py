"""01. Status code triage: reference solution."""

from __future__ import annotations

from dataclasses import dataclass

ACTIONS = {"ok", "fix_request", "reauthenticate", "forbidden", "not_found",
           "conflict", "fix_payload", "back_off", "retry", "give_up"}


@dataclass(frozen=True)
class Triage:
    blame: str
    retryable: bool
    action: str


CLIENT_ACTIONS = {400: "fix_request", 401: "reauthenticate", 403: "forbidden", 404: "not_found",
                  409: "conflict", 422: "fix_payload"}


def triage(method: str, status: int, idempotency_key: bool = False) -> Triage:
    if 200 <= status <= 299:
        return Triage("none", False, "ok")
    if status == 429:
        return Triage("client", True, "back_off")
    if 400 <= status <= 499:
        return Triage("client", False, CLIENT_ACTIONS.get(status, "fix_request"))
    if 500 <= status <= 599:
        # A keyless 5xx on a non-idempotent request may already have had its side effect.
        if method.upper() in {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"} or idempotency_key:
            return Triage("server", True, "retry")
        return Triage("server", False, "give_up")
    raise ValueError(f"cannot triage HTTP status {status}")


if __name__ == "__main__":
    cases = [("GET", 200, False), ("GET", 503, False), ("POST", 503, False), ("POST", 503, True),
             ("post", 429, False), ("DELETE", 418, False), ("GET", 401, False)]
    for method, status, key in cases:
        print(method, status, key, "->", triage(method, status, idempotency_key=key))
