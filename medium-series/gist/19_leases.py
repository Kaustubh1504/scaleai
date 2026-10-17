# 19. Leases with heartbeats, expiry, and stale-worker protection
# Standalone: copy this file as-is. Deps: stdlib

import time
import uuid


def new_item(item_id, payload=None) -> dict:
    return {"id": item_id, "payload": payload, "status": "pending", "attempts": 0,
            "worker": None, "token": None, "expires_at": 0.0}


def reap_expired(items: dict, max_attempts: int = 3, now=None) -> list:
    """Expired leases go back to pending, or to dead after max_attempts. Returns changed ids."""
    now = time.monotonic() if now is None else now
    changed = []
    for it in items.values():
        if it["status"] == "leased" and it["expires_at"] <= now:
            it["status"] = "dead" if it["attempts"] >= max_attempts else "pending"
            it["worker"] = it["token"] = None
            changed.append(it["id"])
    return changed


def acquire(items: dict, worker: str, ttl: float = 30.0, max_attempts: int = 3, now=None):
    """Lease the oldest pending item. Returns (item, token) or None. Hold a lock around calls if threaded."""
    now = time.monotonic() if now is None else now
    reap_expired(items, max_attempts, now)
    for it in items.values():
        if it["status"] == "pending":
            it.update(status="leased", worker=worker, token=uuid.uuid4().hex,
                      expires_at=now + ttl, attempts=it["attempts"] + 1)
            return it, it["token"]
    return None


def _holds(it, token, now) -> bool:
    return it is not None and it["status"] == "leased" and it["token"] == token and it["expires_at"] > now


def heartbeat(items: dict, item_id, token: str, ttl: float = 30.0, now=None) -> bool:
    """Extend the lease. False if the lease expired or someone else holds it now."""
    now = time.monotonic() if now is None else now
    it = items.get(item_id)
    if not _holds(it, token, now):
        return False
    it["expires_at"] = now + ttl
    return True


def complete(items: dict, item_id, token: str, result=None, now=None) -> bool:
    """Only the current holder can complete. Repeating the same completion returns True (idempotent)."""
    now = time.monotonic() if now is None else now
    it = items.get(item_id)
    if it is not None and it["status"] == "completed":
        return it.get("completed_token") == token
    if not _holds(it, token, now):
        return False
    it.update(status="completed", result=result, completed_token=token, token=None, worker=None)
    return True


def fail(items: dict, item_id, token: str, max_attempts: int = 3, now=None) -> bool:
    """Holder gives up: back to pending, or dead after max_attempts."""
    now = time.monotonic() if now is None else now
    it = items.get(item_id)
    if not _holds(it, token, now):
        return False
    it.update(status="dead" if it["attempts"] >= max_attempts else "pending", token=None, worker=None)
    return True
