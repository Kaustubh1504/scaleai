from collections import defaultdict

from .enums import Route

SENIOR_ONLY_SEVERITY = 5


# VERIFIED
def queue_order(item):
    pred, decision = item
    return (-decision.severity, pred.received_at, pred.item_id)


def eligible(reviewer, severity):
    return reviewer.active and reviewer.load < reviewer.capacity and (severity < SENIOR_ONLY_SEVERITY or reviewer.senior)


def assign_expert_queue(predictions, decisions, reviewers):
    """Hand expert items to reviewers in the item's language pool."""
    pools = defaultdict(list)
    for pred in predictions:
        decision = decisions[pred.item_id]
        if decision.route is Route.EXPERT:
            pools[pred.lang].append((pred, decision))

    assignments = {r.reviewer_id: [] for r in reviewers}
    backlog = {}
    for pool, items in sorted(pools.items()):
        members = [r for r in reviewers if r.pool == pool]
        waiting = []
        for pred, decision in sorted(items, key=queue_order):
            candidates = [r for r in members if eligible(r, decision.severity)]
            if not candidates:
                waiting.append(pred.item_id)
                continue
            chosen = min(candidates, key=lambda r: (r.load, r.reviewer_id))
            chosen.load += 1
            assignments[chosen.reviewer_id].append(pred.item_id)
        backlog[pool] = waiting
    return assignments, backlog
