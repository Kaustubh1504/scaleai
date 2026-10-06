import csv
import json
from dataclasses import dataclass
from datetime import datetime

from .utils import clean, norm_id, parse_ts

DEFAULT_MIN_PAYOUT = 1000


@dataclass
class Contributor:
    id: str
    currency: str
    min_payout: int


@dataclass
class Task:
    task_id: str
    contributor_id: str
    task_type: str
    status: str
    minutes: int
    assigned_at: datetime
    submitted_at: datetime


def load_rates(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_contributors(path):
    people = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = norm_id(row["contributor_id"])
            minimum = clean(row["min_payout_usd_cents"])
            people[cid] = Contributor(
                id=cid,
                currency=clean(row["currency"]).upper() or "USD",
                min_payout=int(minimum) if minimum else DEFAULT_MIN_PAYOUT,
            )
    return people


def load_tasks(path):
    tasks = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            minutes = clean(row["minutes"])
            tasks.append(Task(
                task_id=norm_id(row["task_id"]),
                contributor_id=norm_id(row["contributor_id"]),
                task_type=clean(row["task_type"]).lower(),
                status=clean(row["status"]).lower(),
                minutes=int(minutes) if minutes else 0,
                assigned_at=parse_ts(row["assigned_at"]),
                submitted_at=parse_ts(row["submitted_at"]),
            ))
    return tasks
