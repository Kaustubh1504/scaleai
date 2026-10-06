from collections import defaultdict

from .models import DECIDED

REVIEW_ACTIONS = {"pass": "passed", "request_changes": "changes", "reject": "rejected"}


def cycle_hours(tasks):
    """Hours from first submission to the final decision, for decided tasks."""
    out = {}
    for task in tasks:
        if task.state in DECIDED:
            elapsed = task.decided_at - task.submitted_at
            out[task.task_id] = round(elapsed.total_seconds() / 3600, 1)
    return out


def reviewer_stats(accepted):
    stats = defaultdict(lambda: {"passed": 0, "changes": 0, "rejected": 0})
    for event in accepted:
        if event.action == "claim":
            stats[event.actor]
        elif event.action in REVIEW_ACTIONS:
            stats[event.actor][REVIEW_ACTIONS[event.action]] += 1
    return dict(sorted(stats.items()))
