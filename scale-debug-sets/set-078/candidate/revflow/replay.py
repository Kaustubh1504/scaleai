from .clock import claim_deadline, claim_expired
from .machine import actor_allowed, next_state
from .models import State, Transition


def _release_if_expired(task, now, ttl):
    if task.state is State.IN_REVIEW and claim_expired(claim_deadline(task.claim_at, ttl), now):
        task.state = State.SUBMITTED
        task.claim_holder = task.claim_at = None


def replay(events, tasks, people, settings):
    """Apply events in time order (ties: file order). Returns (transitions, violations)."""
    ttl, max_rework = settings["claim_ttl_minutes"], settings["max_rework"]
    transitions, violations = [], []

    def violation(ev, reason):
        violations.append({"line": ev.line, "task": ev.task_id, "action": ev.action, "reason": reason})

    for ev in sorted(events, key=lambda e: (e.ts, e.line)):
        task = tasks.get(ev.task_id)
        if task is None:
            violation(ev, "unknown task")
            continue
        _release_if_expired(task, ev.ts, ttl)
        if not actor_allowed(people.get(ev.actor), ev.action):
            violation(ev, "actor not allowed")
            continue
        rework_after = task.rework + 1 if ev.action == "reject" else task.rework
        target = next_state(task.state, ev.action, rework_after, max_rework)
        if target is None:
            violation(ev, "invalid transition")
            continue
        if ev.action in ("approve", "reject") and ev.actor != task.claim_holder:
            violation(ev, "not claim holder")
            continue
        transitions.append(Transition(ev.ts, task.task_id, ev.actor, ev.action, task.claim_at))
        task.state, task.rework = target, rework_after
        if ev.action == "claim_review":
            task.claim_holder, task.claim_at = ev.actor, ev.ts
        else:
            task.claim_holder = task.claim_at = None
        if target is State.APPROVED:
            task.approved_at = ev.ts

    for task in tasks.values():
        _release_if_expired(task, settings["as_of"], ttl)
    return transitions, violations
