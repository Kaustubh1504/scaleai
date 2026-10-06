from datetime import timedelta

SLA_HOURS = {1: 2, 2: 8, 3: 24}


def review_queue(predictions, decisions):
    pending = [p for p in predictions if decisions[p.item_id].decision == "human"]
    # most urgent first, then oldest
    return sorted(pending, key=lambda p: (p.priority, p.received_at, p.item_id))


def due_at(pred):
    return pred.received_at + timedelta(hours=SLA_HOURS[pred.priority])


def pick_reviewer(pred, reviewers):
    candidates = [r for r in reviewers.values()
                  if r.active and pred.language in r.languages and r.remaining > 0]
    if not candidates:
        return None
    return min(candidates, key=lambda r: (-r.remaining, r.id))


def assign(queue, reviewers):
    unassigned = []
    for pred in queue:
        reviewer = pick_reviewer(pred, reviewers)
        if reviewer is None:
            unassigned.append(pred.item_id)
        else:
            reviewer.assigned.append(pred.item_id)
    return unassigned
