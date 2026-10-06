from .models import Decision


# VERIFIED
def assign_reviewers(routed, reviewers):
    """Give each review item (in item id order) to the least-loaded eligible reviewer.

    Returns the ids of items nobody could take.
    """
    loads = {r.reviewer_id: 0 for r in reviewers}
    backlog = []
    for item in sorted((r for r in routed if r.decision is Decision.HUMAN_REVIEW),
                       key=lambda r: r.prediction.item_id):
        eligible = [rv for rv in reviewers
                    if rv.active and item.prediction.task in rv.skills and loads[rv.reviewer_id] < rv.capacity]
        if not eligible:
            backlog.append(item.prediction.item_id)
            continue
        chosen = min(eligible, key=lambda rv: (loads[rv.reviewer_id], rv.reviewer_id))
        loads[chosen.reviewer_id] += 1
        item.reviewer = chosen.reviewer_id
    return backlog
