from pathlib import Path

from .dedupe import dedupe
from .loader import load_config, load_items
from .sampler import val_sample
from .splitter import SPLITS, assign
from .stats import avg, tally

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def clean_items(items, config):
    unlabeled, excluded, usable = [], [], []
    for item in items:
        if not item.label:
            unlabeled.append(item.item_id)
        elif not item.consent or any(tag in config["exclude_tags"] for tag in item.tags):
            excluded.append(item.item_id)
        else:
            usable.append(item)
    return usable, sorted(unlabeled), sorted(excluded)


def split_stats(by_split):
    stats = {}
    tokens = 0
    for split in SPLITS:
        members = by_split[split]
        for item in members:
            tokens += item.tokens
        stats[split] = {
            "size": len(members),
            "labels": dict(sorted(tally(it.label for it in members).items())),
            "avg_tokens": avg(tokens, len(members)),
        }
    return stats


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    config = load_config(data_dir / "config.json")
    items = load_items(data_dir / "items.csv")

    usable, unlabeled, excluded = clean_items(items, config)
    kept, duplicates = dedupe(usable)
    doc_splits, by_split = assign(kept, config["pinned_test_docs"])
    return {
        "dropped": {"unlabeled": unlabeled, "excluded": excluded, "duplicate": duplicates},
        "doc_splits": doc_splits,
        "val_sample": val_sample(by_split["val"], config["val_cap_per_label"]),
        "splits": split_stats(by_split),
    }
