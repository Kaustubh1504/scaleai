import csv
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def parse_time(text):
    text = clean(text)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time {text!r}")


def load_config(path=None):
    with open(path or DATA_DIR / "config.json", encoding="utf-8") as fh:
        return json.load(fh)


class PriceOrigin:
    """The slow pricing service the cache sits in front of."""

    def __init__(self, path=None):
        self.rows = []
        with open(path or DATA_DIR / "prices.csv", newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                self.rows.append((clean(row["model"]).lower(), clean(row["region"]).lower(),
                                  parse_time(row["effective_from"]), float(clean(row["price"]))))
        self.calls = 0

    # VERIFIED
    def price_at(self, model, region, at):
        best = None
        for m, r, start, price in self.rows:
            if m == model and r == region and start <= at:
                if best is None or start >= best[0]:
                    best = (start, price)
        return None if best is None else best[1]

    def fetch(self, model, region, at):
        self.calls += 1
        return {"model": model, "region": region, "price": self.price_at(model, region, at)}
