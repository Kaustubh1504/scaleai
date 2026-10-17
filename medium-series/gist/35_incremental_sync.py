# 35. Incremental sync (watermark, upserts, tombstones)
# Standalone: copy this file as-is. Deps: stdlib

def apply_changes(store: dict, records, key: str = "id", version: str = "updated_at") -> dict:
    """Upsert into store {id: record}: newer version wins, older or equal replays are skipped.
    Deletes arrive as records with "deleted": true and are kept as tombstones (so an old update
    can't resurrect them). Live rows: [r for r in store.values() if not r.get("deleted")]."""
    counts = {"upserted": 0, "deleted": 0, "skipped": 0, "max_version": None}
    for rec in records:
        k, v = rec[key], rec[version]
        if counts["max_version"] is None or v > counts["max_version"]:
            counts["max_version"] = v
        current = store.get(k)
        if current is not None and current[version] >= v:
            counts["skipped"] += 1
            continue
        store[k] = rec
        counts["deleted" if rec.get("deleted") else "upserted"] += 1
    return counts


def sync(fetch_page, store: dict, state: dict, key: str = "id", version: str = "updated_at") -> dict:
    """fetch_page(since, cursor) -> (records, next_cursor), records changed at/after `since`.
    Applies every page, then advances state["watermark"]. Re-running after a crash is safe:
    replays are skipped. Persist store + state (atomically) after it returns."""
    since, cursor = state.get("watermark"), None
    totals = {"upserted": 0, "deleted": 0, "skipped": 0}
    high = since
    while True:
        records, cursor = fetch_page(since, cursor)
        c = apply_changes(store, records, key, version)
        for k in totals:
            totals[k] += c[k]
        if c["max_version"] is not None and (high is None or c["max_version"] > high):
            high = c["max_version"]
        if not cursor:
            break
    state["watermark"] = high
    return totals
