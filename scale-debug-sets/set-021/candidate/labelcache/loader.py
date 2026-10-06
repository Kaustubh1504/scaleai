import csv
import json
from dataclasses import dataclass
from datetime import datetime

from .utils import clean, norm_locale, norm_model, norm_task, parse_ts


@dataclass
class Request:
    ts: datetime
    op: str
    task_id: str
    model: str
    locale: str


def load_config(path):
    """Return (default ttl in seconds, {model: ttl in seconds})."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    default_ttl = int(raw["default_ttl_seconds"])
    ttls = {norm_model(name): int(clean(ttl)) for name, ttl in raw.get("ttl_seconds", {}).items()}
    return default_ttl, ttls


def load_requests(path):
    requests = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            op = clean(row["op"]).lower()
            requests.append(Request(
                ts=parse_ts(row["ts"]),
                op=op,
                task_id=norm_task(row["task_id"]),
                model=norm_model(row["model"]),
                locale=norm_locale(row["locale"]) if op == "fetch" else "",
            ))
    return requests
