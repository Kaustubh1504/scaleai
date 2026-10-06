import csv
import json

from .utils import clean, norm_id, parse_timestamp, to_cents


def _rows(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            yield {clean(k).lower(): v for k, v in row.items()}


def load_period(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "start": parse_timestamp(raw["start"]),
        "end": parse_timestamp(raw["end"]),
        "fee_percent": float(raw["fee_percent"]),
        "min_payout_cents": to_cents(raw["min_payout"]),
    }


def load_rates(path):
    return {clean(r["task_type"]).lower(): to_cents(r["rate"]) for r in _rows(path)}


def load_tasks(path):
    tasks = []
    for r in _rows(path):
        tasks.append({
            "task_id": norm_id(r["task_id"]),
            "contributor_id": norm_id(r["contributor_id"]),
            "task_type": clean(r["task_type"]).lower(),
            "status": clean(r["status"]).lower(),
            "completed_at": parse_timestamp(r["completed_at"]),
        })
    return tasks


def load_bonuses(path):
    bonuses = []
    for r in _rows(path):
        cid = norm_id(r.get("contributor_id"))
        amount = to_cents(r.get("amount"))
        if cid and amount is not None:
            bonuses.append({"contributor_id": cid, "amount_cents": amount})
    return bonuses
