import csv
import json
from pathlib import Path

from .models import Category
from .utils import clean, parse_bool


def load_categories(path):
    registry = {}
    for item in json.loads(Path(path).read_text(encoding="utf-8")):
        code = clean(item["code"]).lower()
        registry[code] = Category(code, clean(item.get("name")), parse_bool(item.get("active", True)))
    return registry


def _normalise(row):
    return {clean(key).lower(): clean(value) for key, value in row.items() if key is not None}


def read_feed(path):
    """Yield (line_number, row) pairs. The header is line 1."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield reader.line_num, _normalise(row)


def feed_paths(feed_dir):
    return sorted(Path(feed_dir).glob("*.csv"))
