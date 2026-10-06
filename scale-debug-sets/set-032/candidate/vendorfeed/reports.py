from collections import Counter
from pathlib import Path

from .config import load_config, vendor_settings
from .dedupe import dedupe
from .loader import load_vendor
from .validate import partition

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(records):
    labels = Counter(rec.label for rec in records.values())
    tags = Counter(tag for rec in records.values() for tag in set(rec.tags))
    batches = Counter(rec.batch for rec in records.values())
    return {
        "label_counts": dict(sorted(labels.items())),
        "tag_counts": dict(sorted(tags.items())),
        "by_batch": dict(sorted(batches.items())),
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    settings = vendor_settings(load_config(data_dir / "vendors.json"))
    rows_read, accepted, rejected = {}, [], []
    for vendor in sorted(settings):
        loaded = load_vendor(data_dir, vendor, settings[vendor])
        rows_read[vendor] = len(loaded)
        ok, bad = partition(loaded)
        accepted.extend(ok)
        rejected.extend(bad)
    records = dedupe(accepted)
    return {
        "rows_read": rows_read,
        "rejected": {rej.key: list(rej.reasons) for rej in rejected},
        "records": {
            tid: {
                "vendor": rec.vendor,
                "email": rec.email,
                "label": rec.label,
                "batch": rec.batch,
                "submitted": rec.submitted.strftime("%Y-%m-%dT%H:%M"),
                "tags": rec.tags,
            }
            for tid, rec in records.items()
        },
        "summary": summarize(records),
    }
