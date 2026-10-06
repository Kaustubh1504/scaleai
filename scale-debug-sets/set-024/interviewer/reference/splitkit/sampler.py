def val_sample(val_items, cap):
    """Up to `cap` val items per label, lowest item ids first."""
    picked = {}
    for item in sorted(val_items, key=lambda it: it.item_id):
        bucket = picked.setdefault(item.label, [])
        if len(bucket) < cap:
            bucket.append(item.item_id)
    return dict(sorted(picked.items()))
