from collections import defaultdict


# VERIFIED
def newer(candidate, current):
    # equal timestamps: the row read later replaces the earlier one
    return (candidate["updated_at"], candidate["order"]) >= (current["updated_at"], current["order"])


def merge_duplicates(records):
    """Collapse records sharing an email. Returns ({email: record}, rows absorbed)."""
    groups = defaultdict(list)
    for rec in records:
        groups[rec["email"]].append(rec)
    merged, absorbed = {}, 0
    for email, group in groups.items():
        winner = group[0]
        for rec in group[1:]:
            if newer(rec, winner):
                winner = rec
        out = dict(winner)
        out["skills"] = sorted(s for rec in group for s in rec["skills"])
        out["sources"] = sorted(src for rec in group for src in rec["sources"])
        merged[email] = out
        absorbed += len(group) - 1
    return merged, absorbed
