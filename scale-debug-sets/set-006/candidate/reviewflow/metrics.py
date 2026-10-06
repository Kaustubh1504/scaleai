from collections import Counter

from .models import State


def reviewer_table(members, applied):
    table = {m.id: {"approved": 0, "rejected": 0}
             for m in members.values() if m.active and m.can_review}
    for ev in applied:
        if ev.action == "approve":
            table[ev.actor]["approved"] += 1
        elif ev.action == "reject":
            table[ev.actor]["rejected"] += 1
    return table


def annotator_table(members, tasks, applied):
    table = {m.id: {"submitted": 0, "approved": 0}
             for m in members.values() if m.active and m.role == "annotator"}
    for ev in applied:
        if ev.action == "submit":
            table[ev.actor]["submitted"] += 1
    for task in tasks.values():
        if task.state is State.APPROVED:
            table[task.submitter]["approved"] += 1
    return table


def cycle_hours(task):
    return (task.closed_at - task.created_at).seconds / 3600


def state_counts(tasks):
    counts = Counter(t.state.value for t in tasks.values())
    return {s.value: counts.get(s.value, 0) for s in State}
