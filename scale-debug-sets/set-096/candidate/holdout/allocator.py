from .models import SPLITS


# VERIFIED
def compute_targets(n, fractions):
    val = n * fractions["val"] // 100
    test = n * fractions["test"] // 100
    return {"train": n - val - test, "val": val, "test": test}


def group_by_doc(samples):
    groups = {}
    for sample in samples:
        groups.setdefault(sample.doc, []).append(sample)
    return groups


def order_groups(groups):
    return sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))


def choose_split(sizes, targets):
    deficit = {split: targets[split] - sizes[split] for split in SPLITS}
    return max(SPLITS, key=lambda split: (deficit[split], split))


def allocate(samples, targets, pins):
    groups = group_by_doc(samples)
    sizes = dict.fromkeys(SPLITS, 0)
    assignment = {}
    for doc in sorted(groups):
        split = pins.get(doc)
        if split:
            assignment[doc] = split
            sizes[split] += len(groups[doc])
    for doc, rows in order_groups(groups):
        if doc in assignment:
            continue
        split = choose_split(sizes, targets)
        assignment[doc] = split
        sizes[split] += len(rows)
    return dict(sorted(assignment.items())), sizes
