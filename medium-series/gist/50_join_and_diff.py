# 50. Fake HTTP server: scripted replies, call counting, max concurrency
# Standalone: copy this file as-is. Deps: stdlib

def left_join(left, right, left_key, right_key, as_field: str):
    """Attach the matching right row (or None) to a copy of each left row. Returns (rows, unmatched)."""
    index = {right_key(r): r for r in right}
    rows, unmatched = [], []
    for l in left:
        match = index.get(left_key(l))
        if match is None:
            unmatched.append(l)
        rows.append({**l, as_field: match})
    return rows, unmatched


def diff(old: dict, new: dict) -> dict:
    """Snapshots keyed by id -> added / removed / changed ids (sorted)."""
    o, n = set(old), set(new)
    return {"added": sorted(n - o), "removed": sorted(o - n),
            "changed": sorted(k for k in o & n if old[k] != new[k])}
