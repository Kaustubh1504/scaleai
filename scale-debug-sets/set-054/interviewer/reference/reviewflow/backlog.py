from .models import WAITING


def waiting_queue(tasks):
    """Tasks waiting for a reviewer, most important first."""
    waiting = [t for t in tasks if t.state in WAITING]
    waiting.sort(key=lambda t: (-t.priority, t.entered_at, t.task_id))
    return [[t.task_id, t.state.value] for t in waiting]
