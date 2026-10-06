def latest_by_sku(records):
    """One record per SKU: the newest updated_at. Records arrive in feed order."""
    best = {}
    for rec in records:
        current = best.get(rec.sku)
        if current is None or rec.updated_at > current.updated_at:
            best[rec.sku] = rec
    return best


def live_catalog(winners):
    return sorted((r for r in winners.values() if not r.discontinued), key=lambda r: r.sku)
