from collections import Counter
from pathlib import Path

from .pipeline import ingest

DATA = Path(__file__).resolve().parent.parent / "data"
FIELDS = ("name", "vendor", "skills", "hourly_rate", "country", "notes", "sources")


def build_report(data_dir=DATA):
    merged, rejected, absorbed = ingest(data_dir)
    records = {email: {f: rec[f] for f in FIELDS} for email, rec in sorted(merged.items())}
    return {
        "records": records,
        "rejected": rejected,
        "summary": {
            "accepted_by_vendor": dict(sorted(Counter(r["vendor"] for r in records.values()).items())),
            "duplicates_merged": absorbed,
            "rejected_by_reason": dict(sorted(Counter(r["reason"] for r in rejected).items())),
            "countries": dict(sorted(Counter(r["country"] for r in records.values()).items())),
        },
    }
