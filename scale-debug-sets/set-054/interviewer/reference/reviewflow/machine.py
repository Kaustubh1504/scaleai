from .models import (
    AssignmentError, ConflictOfInterest, InvalidTransition, ReviewError, State, UnknownTask,
)


# VERIFIED
def check_claim(task, actor, level):
    if actor == task.author:
        raise ConflictOfInterest(f"{actor} wrote {task.task_id}")
    if level == 2 and actor == task.l1_reviewer:
        raise ConflictOfInterest(f"{actor} already reviewed {task.task_id} at level 1")


class ReviewMachine:
    def __init__(self, tasks):
        self.tasks = {t.task_id: t for t in tasks}
        self.accepted = []
        self.rejected = []

    def handle(self, event):
        try:
            self.apply(event)
        except ConflictOfInterest:
            self.rejected.append((event, "conflict_of_interest"))
        except AssignmentError:
            self.rejected.append((event, "not_assignee"))
        except UnknownTask:
            self.rejected.append((event, "unknown_task"))
        except ReviewError:
            self.rejected.append((event, "invalid_transition"))

    def apply(self, event):
        task = self.tasks.get(event.task_id)
        if task is None:
            raise UnknownTask(event.task_id)
        handler = getattr(self, f"_{event.action}", None)
        if handler is None:
            raise InvalidTransition(f"unknown action {event.action!r}")
        handler(task, event)
        self.accepted.append(event)

    @staticmethod
    def _holder(task):
        if task.state is State.L1_REVIEW:
            return task.l1_reviewer
        if task.state is State.L2_REVIEW:
            return task.l2_reviewer
        raise InvalidTransition(f"{task.task_id} is not under review")

    def _check_holder(self, task, event):
        if event.actor != self._holder(task):
            raise AssignmentError(f"{event.actor} does not hold {task.task_id}")

    def _claim(self, task, event):
        if task.state is State.SUBMITTED:
            check_claim(task, event.actor, 1)
            task.l1_reviewer = event.actor
            task.move(State.L1_REVIEW, event.at)
        elif task.state is State.AWAITING_L2:
            check_claim(task, event.actor, 2)
            task.l2_reviewer = event.actor
            task.move(State.L2_REVIEW, event.at)
        else:
            raise InvalidTransition(f"{task.task_id} can't be claimed in {task.state.value}")

    def _pass(self, task, event):
        self._check_holder(task, event)
        nxt = State.AWAITING_L2 if task.state is State.L1_REVIEW else State.APPROVED
        task.move(nxt, event.at)

    def _request_changes(self, task, event):
        self._check_holder(task, event)
        task.move(State.CHANGES_REQUESTED, event.at)

    def _reject(self, task, event):
        self._check_holder(task, event)
        task.move(State.REJECTED, event.at)

    def _resubmit(self, task, event):
        if task.state is not State.CHANGES_REQUESTED:
            raise InvalidTransition(f"{task.task_id} has no requested changes")
        if event.actor != task.author:
            raise AssignmentError(f"only {task.author} can resubmit {task.task_id}")
        task.revision += 1
        task.l1_reviewer = task.l2_reviewer = None
        task.move(State.SUBMITTED, event.at)
