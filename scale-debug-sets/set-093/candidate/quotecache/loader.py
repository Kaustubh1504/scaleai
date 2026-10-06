import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


@dataclass
class Request:
    req_id: str
    ts: datetime
    client: str
    endpoint: str
    sku: str
    region: str
    currency: str


@dataclass
class Invalidation:
    ts: datetime
    sku: str


def clean(value):
    return (value or "").strip()


# VERIFIED
def parse_ts(value):
    text = clean(value)
    if text.isdigit():
        seconds = int(text) / 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_ttls(path):
    with open(path, encoding="utf-8") as fh:
        return {clean(k).lower(): int(v) for k, v in json.load(fh).items()}


def load_clients(path):
    discounts = {}
    for row in _rows(path):
        pct = clean(row["discount_pct"])
        discounts[clean(row["client_id"]).lower()] = float(pct) if pct else 0.0
    return discounts


def load_prices(path):
    prices = {}
    for row in _rows(path):
        key = (clean(row["sku"]).upper(), clean(row["region"]).upper(), clean(row["currency"]).upper())
        prices[key] = float(clean(row["price"]))
    return prices


def load_requests(path):
    return [
        Request(
            req_id=clean(row["req_id"]).lower(),
            ts=parse_ts(row["ts"]),
            client=clean(row["client"]).lower(),
            endpoint=clean(row["endpoint"]).lower(),
            sku=clean(row["sku"]).upper(),
            region=clean(row["region"]).upper(),
            currency=clean(row["currency"]).upper(),
        )
        for row in _rows(path)
    ]


def load_invalidations(path):
    return [Invalidation(parse_ts(row["ts"]), clean(row["sku"]).upper()) for row in _rows(path)]
