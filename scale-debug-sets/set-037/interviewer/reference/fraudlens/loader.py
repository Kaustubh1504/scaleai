import csv
import json
from dataclasses import dataclass
from datetime import datetime

from .money import parse_amount

REQUIRED = ("txn_id", "card_id", "amount", "currency", "timestamp")
TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M")


class MissingFieldError(ValueError):
    def __init__(self, field):
        super().__init__(f"missing {field}")
        self.field = field


@dataclass(frozen=True)
class Transaction:
    txn_id: str
    card_id: str
    amount: float
    currency: str
    country: str
    ts: datetime


@dataclass(frozen=True)
class Card:
    card_id: str
    home_country: str
    daily_limit_usd: float


def parse_timestamp(text):
    value = text.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {text!r}")


def parse_row(row):
    for name in REQUIRED:
        if not (row.get(name) or "").strip():
            raise MissingFieldError(name)
    return Transaction(
        txn_id=row["txn_id"].strip().upper(),
        card_id=row["card_id"].strip().lower(),
        amount=parse_amount(row["amount"]),
        currency=row["currency"].strip().upper(),
        country=(row.get("country") or "").strip().upper(),
        ts=parse_timestamp(row["timestamp"]),
    )


def load_transactions(path):
    """(transactions in time order, rejected rows in file order)."""
    txns, rejected = [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            txn_id = (row.get("txn_id") or "").strip().upper()
            try:
                txns.append(parse_row(row))
            except MissingFieldError as exc:
                rejected.append({"txn_id": txn_id, "reason": f"missing:{exc.field}"})
            except ValueError:
                rejected.append({"txn_id": txn_id, "reason": "unparseable"})
    return sorted(txns, key=lambda t: t.ts), rejected


def load_cards(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        c["card_id"].strip().lower(): Card(c["card_id"].strip().lower(), c["home_country"].strip().upper(),
                                           float(c["daily_limit_usd"]))
        for c in raw["cards"]
    }


def load_rates(path):
    with open(path, encoding="utf-8") as fh:
        return {k.strip().upper(): float(v) for k, v in json.load(fh)["to_usd"].items()}
