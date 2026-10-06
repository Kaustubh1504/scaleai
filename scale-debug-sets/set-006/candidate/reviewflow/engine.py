from .transitions import HANDLERS


def replay(tasks, members, events):
    """Apply events in order. Returns (applied events, invalid event ids)."""
    applied, invalid = [], []
    for event in events:
        task = tasks.get(event.task_id)
        actor = members.get(event.actor)
        handler = HANDLERS.get(event.action)
        if task is None or actor is None or not actor.active or handler is None:
            invalid.append(event.event_id)
            continue
        if not handler(task, actor, event):
            invalid.append(event.event_id)
            continue
        task.history.append((event.at, event.action, actor.id))
        applied.append(event)
    return applied, invalid
