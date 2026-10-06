from .models import State


# VERIFIED
def priority_key(task):
    """Higher priority number first, then the oldest task, then task id."""
    return (-task.priority, task.created, task.task_id)


def build_queue(tasks, paused):
    """Ids of submitted tasks waiting for review, most urgent first, excluding paused projects."""
    queue = sorted((t for t in tasks.values() if t.state is State.SUBMITTED), key=priority_key)
    for task in queue:
        if task.project in paused:
            queue.remove(task)
    return [t.task_id for t in queue]
