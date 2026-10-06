from .textnorm import fingerprint


def pick_original(copies):
    # the first-created copy is the original; equal dates fall back to the id
    return min(copies, key=lambda s: (s.created, s.sample_id))


def dedupe(samples):
    """Return (kept samples in input order, {duplicate id: kept id})."""
    buckets = {}
    for sample in samples:
        buckets.setdefault(fingerprint(sample.text), []).append(sample)
    keep, duplicates = set(), {}
    for copies in buckets.values():
        original = pick_original(copies)
        keep.add(original.sample_id)
        for sample in copies:
            if sample is not original:
                duplicates[sample.sample_id] = original.sample_id
    return [s for s in samples if s.sample_id in keep], dict(sorted(duplicates.items()))
