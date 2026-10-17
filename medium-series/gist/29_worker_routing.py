# 29. Worker routing: round robin with failover, least loaded, heartbeats
# Standalone: copy this file as-is. Deps: stdlib

def new_worker(worker_id: str, seq: int, now: float) -> dict:
    return {"id": worker_id, "seq": seq, "state": "active", "last_seen": now,
            "in_flight": 0, "capacity": 1, "cooldown_until": None}


def rotation(workers: list, last_seq=None) -> list:
    """One round-robin pass: workers registered after the last one tried, then wrap around.
    `workers` is in registration order with increasing "seq". Works if the last tried worker was removed."""
    if last_seq is None:
        return list(workers)
    return [w for w in workers if w["seq"] > last_seq] + [w for w in workers if w["seq"] <= last_seq]


def least_loaded(workers: list, load, eligible=lambda w: True):
    """Eligible worker with the lowest load(w); ties go to the earliest in the list. None if none eligible."""
    best = None
    for w in workers:
        if eligible(w) and (best is None or load(w) < load(best)):
            best = w
    return best


def state_at(worker: dict, now: float) -> str:
    """Overloaded workers become active again once their cooldown has passed."""
    if worker["state"] == "overloaded" and worker["cooldown_until"] is not None and now >= worker["cooldown_until"]:
        worker.update(state="active", cooldown_until=None)
    return worker["state"]


def on_heartbeat(workers: dict, payload, now: float, cooldown: float = 5.0) -> bool:
    """Apply a heartbeat {"worker_id", "in_flight", "capacity", ...}. Ignores malformed payloads and unknown ids.
    Uses OUR clock (now), never payload["ts"]. Load decides state, even for an unreachable worker."""
    def is_int(v):
        return isinstance(v, int) and not isinstance(v, bool)

    if not (isinstance(payload, dict) and isinstance(payload.get("worker_id"), str)
            and is_int(payload.get("in_flight")) and is_int(payload.get("capacity"))
            and payload["in_flight"] >= 0 and payload["capacity"] >= 1):
        return False
    w = workers.get(payload["worker_id"])
    if w is None:
        return False
    w.update(last_seen=now, in_flight=payload["in_flight"], capacity=payload["capacity"])
    if payload["in_flight"] >= payload["capacity"]:
        w.update(state="overloaded", cooldown_until=now + cooldown)
    else:
        w.update(state="active", cooldown_until=None)
    return True


def check_health(workers: dict, now: float, timeout: float) -> list:
    """Silent for MORE than `timeout` seconds -> unreachable. Never revives a worker (only heartbeats do)."""
    changed = []
    for wid, w in workers.items():
        if now - w["last_seen"] > timeout and w["state"] != "unreachable":
            w["state"] = "unreachable"
            changed.append(wid)
    return changed
