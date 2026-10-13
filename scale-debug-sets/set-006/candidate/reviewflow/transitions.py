from .models import State

MAX_REWORK = 3

# claim: the task must be queued and the actor must be an annotator. The task becomes claimed and the actor becomes its assignee.
# release: the task must be claimed by this actor. It goes back to queued with no assignee.
# submit: the task must be claimed by this actor. It becomes submitted, and the actor is recorded as its submitter.
# approve: the task must be submitted and the actor must be a reviewer or a lead. The task becomes approved, and that moment is its close time.
# reject: same conditions as approve. The task's rework count goes up by one and its assignee is cleared. When the rework count reaches 3 the task becomes escalated (closed at that moment); otherwise it goes back to queued.


def claim(task, actor, event):
    if task.state is not State.QUEUED or actor.role != "annotator":
        return False
    task.state = State.CLAIMED
    task.assignee = actor.id
    return True

# release: the task must be claimed by this actor. It goes back to queued with no assignee.

def release(task, actor, event):
    if task.state is not State.CLAIMED or task.assignee != actor.id:
        return False
    task.state = State.QUEUED
    task.assignee = None
    return True

# submit: the task must be claimed by this actor. It becomes submitted, and the actor is recorded as its submitter.

def submit(task, actor, event):
    if task.state is not State.CLAIMED or task.assignee != actor.id:
        return False
    task.state = State.SUBMITTED
    task.submitter = actor.id
    return True


def _reviewable(task, actor):
    if task.state is not State.SUBMITTED:
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
