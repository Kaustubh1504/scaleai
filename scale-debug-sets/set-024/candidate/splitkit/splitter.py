import hashlib

SPLITS = ("train", "val", "test")


def bucket_for(doc_id):
    return int(hashlib.md5(doc_id.encode("utf-8")).hexdigest(), 16) % 100


# VERIFIED
def split_for(doc_id, pinned):
    if doc_id in pinned:
        return "test"
    bucket = bucket_for(doc_id)
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "val"
    return "test"


def assign(items, pinned):
    doc_splits = {}
    by_split = {name: [] for name in SPLITS}
    for item in items:
        split = doc_splits.setdefault(item.doc_id, split_for(item.doc_id, pinned))
        by_split[split].append(item)
    return dict(sorted(doc_splits.items())), by_split
