from dataclasses import replace


def rank(rec):
    # newest submission first; on equal times the more trusted vendor
    return (rec.submitted, rec.priority)


def merge(copies):
    winner = max(copies, key=rank)
    tags = sorted(tag for rec in copies for tag in rec.tags)
    return replace(winner, tags=tags)


def dedupe(records):
    groups = {}
    for rec in records:
        groups.setdefault(rec.task_id, []).append(rec)
    return {tid: merge(groups[tid]) for tid in sorted(groups)}
