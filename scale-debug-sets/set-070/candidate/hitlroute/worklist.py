from collections import defaultdict


def urgency(item):
    pred = item.prediction
    confidence = pred.confidence if pred.confidence is not None else -1.0
    # priority 1 is the most urgent; then least confident
    return (-pred.priority, confidence)


def build_worklists(routed):
    lists = defaultdict(list)
    for item in routed:
        if item.reviewer:
            lists[item.reviewer].append(item)
    worklists = {}
    for rid, items in sorted(lists.items()):
        items.sort(key=lambda i: i.prediction.item_id)  # oldest first among equals (sort is stable)
        items.sort(key=urgency)
        worklists[rid] = [i.prediction.item_id for i in items]
    return worklists
