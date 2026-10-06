from collections import Counter
from itertools import groupby


def majority(labels):
    counts = Counter(labels)
    # most frequent label; alphabetical among equals
    return counts.most_common(1)[0][0]


def group_labels(samples):
    by_group = list(samples)
    return {gid: majority([s.label for s in rows])
            for gid, rows in groupby(by_group, key=lambda s: s.group_id)}


def strata(labels_by_group):
    out = {}
    for gid, label in labels_by_group.items():
        out.setdefault(label, []).append(gid)
    return {label: sorted(gids) for label, gids in out.items()}
