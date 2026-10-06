from collections import defaultdict

from .models import Result, Tier


def within_window(vote, item):
    return item.closes_at is None or vote.submitted_at <= item.closes_at


def expert_votes(votes, annotators, label):
    return sum(1 for v in votes if v.label == label and annotators[v.annotator_id].tier is Tier.EXPERT)


# VERIFIED
def pick_label(totals, experts):
    return min(totals, key=lambda label: (-totals[label], -experts[label], label))


def decide(item, votes, annotators, weights, queue):
    counted = [v for v in votes if within_window(v, item)]
    if len(counted) < item.min_votes:
        return Result(item.id, "pending", None, None, len(counted))
    totals = defaultdict(float)
    for vote in counted:
        totals[vote.label] += weights[annotators[vote.annotator_id].tier]
    experts = {label: expert_votes(counted, annotators, label) for label in totals}
    winner = pick_label(totals, experts)
    agreement = round(totals[winner] / sum(totals.values()), 3)
    status = "accepted" if agreement >= queue.threshold else "escalated"
    dissent = any(annotators[v.annotator_id].tier is Tier.EXPERT and v.label != winner for v in counted)
    return Result(item.id, status, winner, agreement, len(counted), dissent)


def resolve(items, votes, annotators, weights, queues):
    by_item = defaultdict(list)
    for vote in votes:
        by_item[vote.item_id].append(vote)
    return {
        item_id: decide(item, by_item[item_id], annotators, weights, queues[item.queue])
        for item_id, item in sorted(items.items())
    }
