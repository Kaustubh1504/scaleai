from collections import defaultdict

from .hashing import hash_order


def take_held_out(pool):
    """Move held-out speakers out of `pool` (in place) and return them."""
    held = []
    for spk in pool:
        if spk.held_out:
            pool.remove(spk)
            held.append(spk)
    return held


def allocate(pool, config):
    ordered = hash_order(pool, config["seed"])
    n_test = len(ordered) * config["test_percent"] // 100
    n_val = len(ordered) * config["val_percent"] // 100
    plan = {}
    for spk in ordered[:n_test]:
        plan[spk.id] = "test"
    for spk in ordered[n_test:n_test + n_val]:
        plan[spk.id] = "val"
    for spk in ordered[n_test + n_val:]:
        plan[spk.id] = "train"
    return plan


def assign_speakers(active_speakers, config):
    """active_speakers: speakers with at least one usable clip. Returns {speaker_id: split}."""
    strata = defaultdict(list)
    for spk in sorted(active_speakers, key=lambda s: s.id):
        strata[spk.accent].append(spk)
    assignment = {}
    for accent in sorted(strata):
        pool = strata[accent]
        for spk in take_held_out(pool):
            assignment[spk.id] = "test"
        assignment.update(allocate(pool, config))
    return assignment
