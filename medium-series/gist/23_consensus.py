# 23. Fake HTTP server: scripted replies, call counting, max concurrency
# Standalone: copy this file as-is. Deps: stdlib

from collections import Counter


def consensus(labels: list[str], min_votes: int = 3, threshold: tuple[int, int] = (2, 3)) -> dict:
    """Majority vote. threshold=(2, 3) means top label needs >= 2/3 of votes (integer math, no float bugs)."""
    votes = Counter(labels)
    total = sum(votes.values())
    if not total:
        return {"votes": {}, "total": 0, "agreement": None, "status": "insufficient", "label": None}
    label, top = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    out = {"votes": dict(votes), "total": total, "agreement": round(top / total, 2)}
    if total < min_votes:
        return {**out, "status": "insufficient", "label": None}
    num, den = threshold
    if top * den >= total * num:
        return {**out, "status": "agreed", "label": label}
    return {**out, "status": "disputed", "label": None}
