SPLITS = ("train", "val", "test")


def split_groups(strata_map, val_percent, test_percent):
    assignment = {}
    for label in sorted(strata_map):
        ordered = strata_map[label]
        n = len(ordered)
        n_test = n * test_percent // 100
        n_val = n * val_percent // 100
        for gid in ordered[:n_test]:
            assignment[gid] = "test"
        for gid in ordered[n_test:n_val]:
            assignment[gid] = "val"
        for gid in ordered[n_test + n_val:]:
            assignment[gid] = "train"
    return assignment


# VERIFIED
def apply_cap(train_samples, cap):
    kept, capped = [], []
    taken = {}
    for sample in sorted(train_samples, key=lambda s: (s.created_at, s.sample_id)):
        if taken.get(sample.label, 0) >= cap:
            capped.append(sample.sample_id)
            continue
        taken[sample.label] = taken.get(sample.label, 0) + 1
        kept.append(sample)
    return kept, capped


def build_splits(samples, assignment, cap):
    members = {name: [] for name in SPLITS}
    for sample in samples:
        split = assignment.get(sample.group_id)
        if split is not None:
            members[split].append(sample)
    members["train"], capped = apply_cap(members["train"], cap)
    return members, sorted(capped)
