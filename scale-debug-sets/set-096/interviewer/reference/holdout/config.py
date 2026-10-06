import copy
import json

from .models import DatasetConfig
from . import textnorm


def merge(defaults, overrides):
    """Dataset settings on top of the shared defaults; `fractions` merges key by key."""
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if key == "fractions":
            merged["fractions"].update(value)
        else:
            merged[key] = value
    return merged


def load_datasets(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    configs = []
    for name, overrides in raw["datasets"].items():
        merged = merge(raw["defaults"], overrides)
        configs.append(DatasetConfig(
            name=name,
            file=merged["file"],
            fractions={split: int(pct) for split, pct in merged["fractions"].items()},
            min_quality=float(merged["min_quality"]),
            blocked_licenses=frozenset(textnorm.clean(lic).lower() for lic in merged["blocked_licenses"]),
            pins={textnorm.norm_doc(doc): textnorm.clean(split).lower() for doc, split in merged.get("pins", {}).items()},
        ))
    return configs
