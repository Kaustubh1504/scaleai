from .models import State

MAX_REWORK = 3


def claim(task, actor, event):
    if task.state is not State.QUEUED or actor.role != "annotator":
        return False
    task.state = State.CLAIMED
    task.assignee = actor.id
    return True


def release(task, actor, event):
    if task.state is not State.CLAIMED or task.assignee != actor.id:
        return False
    task.state = State.QUEUED
    task.assignee = None
    return True


def submit(task, actor, event):
    if task.state is not State.CLAIMED or task.assignee != actor.id:
        return False
    task.state = State.SUBMITTED
    task.submitter = actor.id
    return True


def _reviewable(task, actor):
    if task.state != "submitted":
        return False
    return bool(actor.can_review)


def approve(task, actor, event):
    if not _reviewable(task, actor):
        return False
    task.state = State.APPROVED
    task.closed_at = event.at
    return True


# VERIFIED
def reject(task, actor, event):
    if not _reviewable(task, actor):
        return False
    task.rework += 1
    task.assignee = None
    if task.rework >= MAX_REWORK:
        task.state = State.ESCALATED
        task.closed_at = event.at
    else:
        task.state = State.QUEUED
    return True


HANDLERS = {
    "claim": claim,
    "release": release,
    "submit": submit,
    "approve": approve,
    "reject": reject,
}
