from __future__ import annotations
from dataclasses import dataclass

ACTIONS = {"ok", "fix_request", "reauthenticate", "forbidden", "not_found",
           "conflict", "fix_payload", "back_off", "retry", "give_up"}


@dataclass(frozen=True)
class Triage:
    blame: str       # "none" | "client" | "server"
    retryable: bool
    action: str


IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


def triage(method: str, status: int, idempotency_key: bool = False) -> Triage:
    if str(status).startswith("2"):
        return Triage('none',False,"ok")
    elif status == 400:
        return Triage("client",False,"fix_request")
    elif status == 401:
        return Triage("client",False,"reauthenticate")
    elif status == 403:
        return Triage("client",False,"forbidden")
    elif status == 404:
        return Triage("client",False,"not_found")
    elif status == 409:
        return Triage("client",False,"conflict")
    elif status == 422:
        return Triage("client",False,"fix_payload")
    elif status == 429:
        return Triage("client",True,"back_off")
    elif str(status).startswith("4"):
        return Triage("client",False,"fix_request")
    elif str(status).startswith("5"):
        if not idempotency_key and method.upper() not in IDEMPOTENT_METHODS: return Triage("server",False,"give_up")
        return Triage("server",True,"retry")
        
        
    raise ValueError("Not a valid status code")
        


if __name__ == "__main__":
    cases = [
        ("GET", 200, False), ("GET", 503, False), ("POST", 503, False), ("POST", 503, True),
        ("post", 429, False), ("DELETE", 418, False), ("GET", 401, False),
    ]
    for method, status, key in cases:
        print(f"{method:<7} {status} key={key!s:<5} ->", triage(method, status, idempotency_key=key))
