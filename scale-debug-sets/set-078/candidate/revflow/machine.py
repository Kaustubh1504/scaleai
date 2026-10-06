from .models import State

ROLES = {
    "claim_label": {"annotator"},
    "submit": {"annotator"},
    "claim_review": {"reviewer", "senior"},
    "approve": {"reviewer", "senior"},
    "reject": {"reviewer", "senior"},
    "resolve": {"senior"},
}

_TABLE = {
    (State.QUEUED, "claim_label"): State.LABELING,
    (State.LABELING, "submit"): State.SUBMITTED,
    (State.SUBMITTED, "claim_review"): State.IN_REVIEW,
    (State.IN_REVIEW, "approve"): State.APPROVED,
    (State.IN_REVIEW, "reject"): State.LABELING,
    (State.ESCALATED, "resolve"): State.APPROVED,
}


# VERIFIED
def next_state(state, action, rework_after, max_rework):
    """Target state, or None when the action is not allowed from `state`.

    A reject sends the task back to labeling, not to a rejected state; it escalates
    once the task has been reworked max_rework times.
    """
    target = _TABLE.get((state, action))
    if action == "reject" and target is not None and rework_after >= max_rework:
        return State.ESCALATED
    return target


def actor_allowed(person, action):
    return person is not None and person.active and person.role in ROLES.get(action, set())
