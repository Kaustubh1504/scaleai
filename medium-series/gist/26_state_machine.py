# 26. Task state machine (allowed transitions, idempotent, audited)
# Standalone: copy this file as-is. Deps: stdlib

import time

TRANSITIONS = {
    "pending": {"leased", "cancelled"},
    "leased": {"pending", "completed", "failed"},
    "failed": {"pending", "dead"},
    "completed": set(),
    "dead": set(),
    "cancelled": set(),
}


class InvalidTransition(Exception):
    """Map to 409 Conflict."""


def transition(task: dict, to: str, transitions=TRANSITIONS, audit=None) -> bool:
    """Move task["status"] to `to`. Same state again -> no-op, returns False (safe to retry).
    Not allowed -> InvalidTransition. Appends {"id", "from", "to", "at"} to `audit` if given."""
    current = task["status"]
    if current == to:
        return False
    if to not in transitions.get(current, set()):
        raise InvalidTransition(f"{task.get('id')}: {current} -> {to} not allowed")
    task["status"] = to
    if audit is not None:
        audit.append({"id": task.get("id"), "from": current, "to": to, "at": time.time()})
    return True
