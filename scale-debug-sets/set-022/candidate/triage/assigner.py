# VERIFIED
def pick_reviewer(candidates, remaining):
    return min(candidates, key=lambda r: (-remaining[r.id], r.id)) if candidates else None


def assign(queue, reviewers):
    active = [r for r in reviewers if r.active]
    remaining = {r.id: r.capacity for r in active}
    assignments = {r.id: [] for r in active}
    backlog = []
    for decision in queue:
        pred = decision.prediction
        candidates = [r for r in active if pred.lang in r.languages and remaining[r.id] > 0]
        chosen = pick_reviewer(candidates, remaining)
        if chosen is None:
            backlog.append(pred.pred_id)
            continue
        assignments[chosen.id].append(pred.pred_id)
        remaining[chosen.id] -= 1
    return assignments, backlog
