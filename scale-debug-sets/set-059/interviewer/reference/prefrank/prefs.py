def latest_only(comparisons):
    """One comparison per (rater, prompt, pair): the latest created_at, later row on ties.
    Returned in (created_at, row) order."""
    best = {}
    for c in comparisons:
        key = (c.rater, c.prompt_id, c.pair)
        cur = best.get(key)
        if cur is None or (c.created_at, c.row) > (cur.created_at, cur.row):
            best[key] = c
    return sorted(best.values(), key=lambda c: (c.created_at, c.row))
