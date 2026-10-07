"""Read the three input files and clean ids, devices, timestamps and amounts."""
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M")


@dataclass(frozen=True)
class Account:
    id: str
    referred_by: str | None
    signup_at: datetime
    device: str | None


@dataclass(frozen=True)
class Deposit:
    id: str
    account: str
    amount: Decimal
    status: str
    at: datetime


def clean_id(raw):
    return (raw or "").strip().lower()


def clean_device(raw):
    return (raw or "").strip() or None


def parse_time(raw):
    text = (raw or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {raw!r}")


def parse_amount(raw):
    text = (raw or "").strip().lstrip("$").replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def load_accounts(data_dir=DATA_DIR):
    """Return {account_id: Account} in file order. Referrers must be known accounts."""
    with open(Path(data_dir) / "accounts.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    known = {clean_id(row["account_id"]) for row in rows}
    accounts = {}
    for row in rows:
        acct_id = clean_id(row["account_id"])
        referrer = clean_id(row["referred_by"])
        accounts[acct_id] = Account(
            id=acct_id,
            referred_by=referrer if referrer in known else None,
            signup_at=parse_time(row["signup_at"]),
            device=clean_device(row["device_id"]),
        )
    return accounts


def load_deposits(accounts, data_dir=DATA_DIR):
    deposits = []
    with open(Path(data_dir) / "deposits.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            acct_id = clean_id(row["account_id"])
            amount = parse_amount(row["amount"])
            if acct_id not in accounts or amount is None:
                continue
            deposits.append(Deposit(
                id=row["deposit_id"].strip(),
                account=acct_id,
                amount=amount,
                status=row["status"].strip().lower(),
                at=parse_time(row["deposited_at"]),
            ))
    return deposits


def load_logins(accounts, data_dir=DATA_DIR):
    """Return ([(account_id, ip), ...] for known accounts, set of shared network ips)."""
    with open(Path(data_dir) / "logins.json", encoding="utf-8") as fh:
        raw = json.load(fh)
    shared = {ip.strip() for ip in raw.get("shared_networks", [])}
    logins = []
    for item in raw["logins"]:
        acct_id = clean_id(item.get("account"))
        ip = (item.get("ip") or "").strip()
        if acct_id in accounts and ip:
            logins.append((acct_id, ip))
    return logins, shared
