from pathlib import Path

from .dedupe import merge_duplicates
from .normalize import build_record
from .readers import read_export
from .schema import MissingField

# first matching class decides the reason
REASONS = [(MissingField, "missing_field"), (ValueError, "invalid_value")]


def ingest(data_dir):
    """Read every export in name order. Returns (records by email, rejected rows, rows absorbed)."""
    records, rejected = [], []
    order = 0
    for path in sorted(Path(data_dir).iterdir()):
        if path.suffix not in (".csv", ".json"):
            continue
        for row_no, row in enumerate(read_export(path), start=1):
            order += 1
            try:
                records.append(build_record(row, path.stem, order))
            except ValueError as exc:
                reason = next(label for cls, label in REASONS if isinstance(exc, cls))
                rejected.append({"file": path.name, "row": row_no, "reason": reason})
    merged, absorbed = merge_duplicates(records)
    return merged, rejected, absorbed
