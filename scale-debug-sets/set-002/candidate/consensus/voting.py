from collections import defaultdict

from .models import Consensus

MIN_ACCURACY = 0.5
MIN_VOTES = 2


def is_blocked(row):
    return row.accuracy <= MIN_ACCURACY


def mark_blocked(table):
    for row in table.values():
        row.blocked = is_blocked(row)
    return table


def tally(votes, weights):
    totals = {}
    for ann in votes:
        totals[ann.label] = totals.get(ann.label, 0.0) + weights[ann.annotator_id]
    return totals


def pick_winner(totals):
    # heaviest label wins; alphabetical on ties
    return max(totals, key=totals.get)


def resolve(task_ids, annotations, gold, table):
    weights = {aid: row.accuracy for aid, row in table.items() if not row.blocked}
    by_task = defaultdict(list)
    for ann in annotations:
        if ann.annotator_id in weights:
            by_task[ann.task_id].append(ann)

    results = {}
    for tid in task_ids:
        if tid in gold:
            continue
        votes = by_task.get(tid, [])
        if len(votes) < MIN_VOTES:
            results[tid] = Consensus(tid, "needs_more_votes", None, None, len(votes))
            continue
        totals = tally(votes, weights)
        winner = pick_winner(totals)
        confidence = round(totals[winner] / sum(totals.values()), 3)
        results[tid] = Consensus(tid, "resolved", winner, confidence, len(votes))
    return results
