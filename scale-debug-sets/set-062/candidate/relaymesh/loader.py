"""Parse workers.json, requests.csv and health.csv."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from relaymesh.models import HealthEvent, Request, Worker, WorkerState

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_MAX_INFLIGHT = 2
DEFAULT_ZONE = "central"


def clean(value) -> str:
    return str(value if value is not None else "").strip()


def norm_id(value) -> str:
    return clean(value).lower()


def parse_state(value) -> WorkerState:
    return WorkerState(clean(value).lower())


def parse_clock_ms(value) -> int:
    """`12:00:03` or `12:00:03.250`, as ms after the 12:00:00 window start."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?", clean(value))
    if not match:
        raise ValueError(f"unrecognised time: {value!r}")
    h, m, s, frac = match.groups()
    ms = int((frac or "0").ljust(3, "0"))
    return ((int(h) - 12) * 3600 + int(m) * 60 + int(s)) * 1000 + ms


def parse_duration_ms(value) -> int:
    """`850ms`, `1.2s` or a bare number of milliseconds."""
    text = clean(value).lower()
    if text.endswith("ms"):
        return int(float(text[:-2]))
    if text.endswith("s"):
        return int(round(float(text[:-1]) * 1000))
    return int(float(text))


def load_workers(path: Path | None = None) -> list[Worker]:
    path = path or DATA_DIR / "workers.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    workers = []
    for item in raw["workers"]:
        workers.append(Worker(
            worker_id=norm_id(item["id"]),
            zone=norm_id(item["zone"]),
            weight=float(item["weight"]),
            max_inflight=int(item.get("max_inflight") or DEFAULT_MAX_INFLIGHT),
            state=parse_state(item.get("state", "healthy")),
        ))
    return workers


def load_requests(path: Path | None = None) -> list[Request]:
    path = path or DATA_DIR / "requests.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = [
        Request(
            request_id=norm_id(r["request_id"]),
            zone=norm_id(r["zone"]) or DEFAULT_ZONE,
            arrival_ms=parse_clock_ms(r["arrived_at"]),
            duration_ms=parse_duration_ms(r["duration"]),
        )
        for r in rows
    ]
    return sorted(out, key=lambda r: r.arrival_ms)


def load_health(path: Path | None = None) -> list[HealthEvent]:
    path = path or DATA_DIR / "health.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    events = [
        HealthEvent(at_ms=parse_clock_ms(r["at"]), worker_id=norm_id(r["worker_id"]), state=parse_state(r["state"]))
        for r in rows
    ]
    return sorted(events, key=lambda e: e.at_ms)
