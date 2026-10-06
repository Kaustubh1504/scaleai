import csv
import json

from .models import RawRow


def read_csv_source(path, source):
    """Rows as RawRow; `row` is the data row number (first data row = 1)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [RawRow(source, n, dict(row)) for n, row in enumerate(csv.DictReader(fh), start=1)]


def read_json_source(path, source):
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return [RawRow(source, n, dict(row)) for n, row in enumerate(rows, start=1)]


def read_source(path, source):
    if path.suffix == ".json":
        return read_json_source(path, source)
    return read_csv_source(path, source)
