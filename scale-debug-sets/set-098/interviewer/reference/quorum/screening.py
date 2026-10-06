def rejection_reason(vote, label, items, annotators, queues):
    item = items.get(vote.item_id)
    if item is None:
        return "unknown_item"
    annotator = annotators.get(vote.annotator_id)
    if annotator is None:
        return "unknown_annotator"
    if not annotator.active:
        return "inactive"
    if annotator.queues and item.queue not in annotator.queues:
        return "not_certified"
    if label not in queues[item.queue].labels:
        return "invalid_label"
    return None


def screen(votes, items, annotators, queues, aliases, rejected=None):
    """Return (accepted votes with canonical labels, {vote_id: reason})."""
    rejected = {} if rejected is None else rejected
    kept = []
    for vote in votes:
        label = aliases.get(vote.label, vote.label)
        reason = rejection_reason(vote, label, items, annotators, queues)
        if reason:
            rejected[vote.vote_id] = reason
        else:
            kept.append(vote if label == vote.label else _relabel(vote, label))
    return kept, rejected


def _relabel(vote, label):
    return type(vote)(vote.vote_id, vote.vendor, vote.item_id, vote.annotator_id, label, vote.submitted_at)


def latest_only(votes):
    """Keep each annotator's latest vote per item. Returns (kept, superseded ids)."""
    latest = {}
    superseded = []
    for vote in votes:
        key = (vote.item_id, vote.annotator_id)
        current = latest.get(key)
        if current is None:
            latest[key] = vote
        elif vote.submitted_at >= current.submitted_at:
            superseded.append(current.vote_id)
            latest[key] = vote
        else:
            superseded.append(vote.vote_id)
    return list(latest.values()), sorted(superseded)
