import csv
import json
from datetime import datetime

from .models import Probe, Request, State, Worker

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def norm_id(value):
    return (value or "").strip().upper()


def norm_zone(value):
    return (value or "").strip().lower()


# VERIFIED
def parse_time(value):
    text = (value or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def load_workers(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    workers = []
    for item in raw:
        admin = (item.get("admin") or "active").strip().lower()
        workers.append(Worker(
            worker_id=norm_id(item["id"]),
            zone=norm_zone(item["zone"]),
            weight=int(item["weight"]),
            max_conns=int(item["max_conns"]),
            state=State.DRAINING if admin == "draining" else State.UP,
        ))
    return sorted(workers, key=lambda w: w.worker_id)


def load_probes(path):
    with open(path, newline="", encoding="utf-8") as fh:
        probes = [
            Probe(
                worker_id=norm_id(row["worker_id"]),
                checked_at=parse_time(row["checked_at"]),
                result=(row["result"] or "").strip().lower(),
                latency_ms=int(row["latency_ms"]) if (row["latency_ms"] or "").strip() else None,
            )
            for row in csv.DictReader(fh)
        ]
    return sorted(probes, key=lambda p: p.checked_at)


def load_requests(path):
    requests = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            duration = (row["duration_ms"] or "").strip()
            if not duration:
                continue
            requests.append(Request(
                request_id=norm_id(row["request_id"]),
                zone=norm_zone(row["zone"]),
                arrived_at=parse_time(row["arrived_at"]),
                duration_ms=int(duration),
            ))
    return sorted(requests, key=lambda r: r.arrived_at)
