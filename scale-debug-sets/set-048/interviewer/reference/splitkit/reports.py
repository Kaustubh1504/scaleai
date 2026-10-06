from pathlib import Path

from .loader import load_config, load_samples
from .splitter import SPLITS, build_splits, split_groups
from .strata import group_labels, strata

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def label_counts(members, labels):
    empty = {label: 0 for label in labels}
    counts = {name: dict(empty) for name in SPLITS}
    for name, samples in members.items():
        for sample in samples:
            counts[name][sample.label] += 1
    return counts


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    loaded = load_samples(data_dir / "samples.csv")
    labels_by_group = group_labels(loaded.samples)
    assignment = split_groups(strata(labels_by_group), config["val_percent"], config["test_percent"])
    members, capped = build_splits(loaded.samples, assignment, config["train_cap_per_label"])
    all_labels = sorted({s.label for s in loaded.samples})
    return {
        "excluded": sorted(loaded.excluded),
        "duplicates": sorted(loaded.duplicates),
        "group_labels": dict(sorted(labels_by_group.items())),
        "group_split": dict(sorted(assignment.items())),
        "splits": {name: sorted(s.sample_id for s in members[name]) for name in SPLITS},
        "capped": capped,
        "label_counts": label_counts(members, all_labels),
    }
