from itertools import groupby
from pathlib import Path

from .allocator import allocate, compute_targets
from .config import load_datasets
from .dedupe import dedupe
from .filters import apply_filters
from .loader import load_samples, load_sources

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def label_totals(samples):
    ordered = list(samples)
    return {label: len(list(rows)) for label, rows in groupby(ordered, key=lambda s: s.label)}


def dataset_report(config, sources, data_dir):
    samples = load_samples(data_dir / config.file)
    filtered, dropped = apply_filters(samples, sources, config)
    kept, duplicates = dedupe(filtered)
    targets = compute_targets(len(kept), config.fractions)
    groups, sizes = allocate(kept, targets, config.pins)
    return {
        "kept": len(kept),
        "dropped": dict(sorted(dropped.items())),
        "duplicates": duplicates,
        "targets": targets,
        "groups": groups,
        "sizes": sizes,
        "label_totals": label_totals(kept),
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    sources = load_sources(data_dir / "sources.json")
    return {cfg.name: dataset_report(cfg, sources, data_dir) for cfg in load_datasets(data_dir / "datasets.json")}
