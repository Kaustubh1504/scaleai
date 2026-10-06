from itertools import groupby

MIN_VOTES = 2


def vote(spans):
    """Accepted span key -> number of distinct annotators who marked it."""
    ordered = sorted(spans, key=lambda s: (s.doc_id, s.start))
    accepted = {}
    for key, group in groupby(ordered, key=lambda s: s.key):
        voters = {s.annotator for s in group}
        if len(voters) >= MIN_VOTES:
            accepted[key] = len(voters)
    return accepted
