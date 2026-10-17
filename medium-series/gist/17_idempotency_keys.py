# 17. Idempotency keys on your own POST endpoint
# Standalone: copy this file as-is. Deps: stdlib

import hashlib
import json
import re
import threading
import time

KEY_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
RECORDS: dict = {}               # (scope, key) -> record; persist it (atomically) if it must survive restarts
LOCK = threading.Lock()


def fingerprint(body) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_idempotent(scope: str, key, body, create, ttl: float = 86_400, clock=time.time,
                   records: dict = RECORDS, lock=LOCK):
    """Run create() -> (status, response_body) at most once per (scope, key). Returns (status, body, replayed).

    key None          -> just create()
    key malformed     -> ValueError (map to 400)
    seen, same body   -> the stored response, replayed=True (send header Idempotent-Replayed: true)
    seen, other body  -> (409, ...)
    first still running (concurrent retry) -> (409, ...)
    create() raises or returns non-2xx -> nothing stored; the key can be retried
    record older than ttl -> ignored; the key is reusable
    """
    if key is None:
        status, resp = create()
        return status, resp, False
    if not KEY_RE.fullmatch(key):
        raise ValueError("invalid Idempotency-Key")
    fp, rk = fingerprint(body), (scope, key)
    with lock:
        rec = records.get(rk)
        if rec is not None and clock() >= rec["created_at"] + ttl:
            records.pop(rk)
            rec = None
        if rec is not None:
            if rec["fingerprint"] != fp:
                return 409, {"detail": "Idempotency-Key was used with a different request"}, False
            if rec["state"] == "in_progress":
                return 409, {"detail": "a request with this key is in progress"}, False
            return rec["status"], rec["body"], True
        records[rk] = {"fingerprint": fp, "state": "in_progress", "created_at": clock()}
    try:
        status, resp = create()
    except BaseException:
        with lock:
            records.pop(rk, None)
        raise
    with lock:
        if 200 <= status < 300:
            records[rk].update(state="done", status=status, body=resp)
        else:
            records.pop(rk, None)
    return status, resp, False
