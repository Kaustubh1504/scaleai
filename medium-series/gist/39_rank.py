# 39. Rank with ties (leaderboards)
# Standalone: copy this file as-is. Deps: stdlib

def rank(items, score, tiebreak=None, method: str = "competition", descending: bool = True) -> list:
    """[(rank, item)]. Ties share a rank. competition: 1, 2, 2, 4   dense: 1, 2, 2, 3.
    `tiebreak(item)` orders tied items (e.g. by name) so the output is deterministic."""
    def sort_key(it):
        s = score(it)
        return (-s if descending else s, tiebreak(it) if tiebreak else 0)

    out, prev, current = [], object(), 0
    for i, it in enumerate(sorted(items, key=sort_key), 1):
        s = score(it)
        if s != prev:
            current = i if method == "competition" else current + 1
            prev = s
        out.append((current, it))
    return out
