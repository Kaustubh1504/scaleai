import csv
from collections import defaultdict


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def load_requests(path):
    """shard -> list of {"id", "text"} in file order. Blank texts go to the "skipped" list."""
    shards, skipped = defaultdict(list), []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            item = {"id": norm_id(row["request_id"]), "text": clean(row["text"])}
            shard = norm_id(row["shard"])
            if not item["text"]:
                skipped.append((shard, item["id"]))
                continue
            shards[shard].append(item)
    return dict(sorted(shards.items())), skipped
