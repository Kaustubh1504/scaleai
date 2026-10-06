def tally(labels, counts=None):
    if counts is None:
        counts = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return counts


def avg(total, n):
    return round(total / n, 2) if n else 0.0
