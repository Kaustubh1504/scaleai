import csv
import json
from pathlib import Path


def _norm_keys(row):
    return {str(k).strip().lower(): v for k, v in row.items() if k is not None}


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [_norm_keys(row) for row in csv.DictReader(fh)]


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return [_norm_keys(row) for row in json.load(fh)]


def read_export(path):
    """Rows of one vendor export, keyed by lower-cased column name."""
    path = Path(path)
    if path.suffix == ".json":
        return read_json(path)
    return read_csv(path)
