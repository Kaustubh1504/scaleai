import csv
import json

from .models import LoadResult, Sample
from .utils import clean, norm_group, norm_label, norm_sample, parse_flag, parse_timestamp


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "val_percent": int(raw["val_percent"]),
        "test_percent": int(raw["test_percent"]),
        "train_cap_per_label": int(raw["train_cap_per_label"]),
    }


def load_samples(path):
    result = LoadResult()
    seen = set()
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            label = norm_label(row["label"])
            if not label:
                continue
            sid = norm_sample(row["sample_id"])
            if parse_flag(row.get("exclude")):
                result.excluded.append(sid)
                continue
            key = clean(row["sample_id"])
            if key in seen:
                result.duplicates.append(sid)
                continue
            seen.add(key)
            result.samples.append(Sample(
                sample_id=sid,
                group_id=norm_group(row["group_id"]),
                label=label,
                created_at=parse_timestamp(row["created_at"]),
            ))
    return result
