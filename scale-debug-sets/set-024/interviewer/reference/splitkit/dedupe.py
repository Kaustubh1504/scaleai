def text_key(text):
    return " ".join(text.lower().split())


def pick_keeper(group):
    return min(group, key=lambda it: (it.created, it.item_id))


def dedupe(items):
    """Return (kept items in input order, ids of dropped duplicates sorted)."""
    groups = {}
    for item in items:
        groups.setdefault(text_key(item.text), []).append(item)
    keepers = {id(pick_keeper(group)) for group in groups.values()}
    kept = [it for it in items if id(it) in keepers]
    dropped = sorted(it.item_id for it in items if id(it) not in keepers)
    return kept, dropped
