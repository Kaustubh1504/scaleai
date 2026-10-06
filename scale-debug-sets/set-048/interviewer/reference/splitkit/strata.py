from collections import Counter
from itertools import groupby


def majority(labels):
    counts = Counter(labels)
    # most frequent label; alphabetical among equals
    return min(counts, key=lambda label: (-counts[label], label))


def group_labels(samples):
    by_group = sorted(samples, key=lambda s: s.group_id)
    return {gid: majority([s.label for s in rows])
            for gid, rows in groupby(by_group, key=lambda s: s.group_id)}


def strata(labels_by_group):
    out = {}
    for gid, label in labels_by_group.items():
        out.setdefault(label, []).append(gid)
    return {label: sorted(gids) for label, gids in out.items()}
