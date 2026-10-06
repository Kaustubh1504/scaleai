import csv
import json

from .models import Backend, Probe, Request
from .utils import clean_id, parse_bool, parse_ms

DEFAULT_DURATION_MS = 100


def load_backends(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    backends = {}
    for item in raw["backends"]:
        b = Backend(
            id=clean_id(item["id"]),
            pool=clean_id(item["pool"]),
            weight=int(item.get("weight", 1)),
            max_conns=int(item["max_conns"]),
            enabled=parse_bool(item.get("enabled", True)),
        )
        backends[b.id] = b
    return backends


def load_requests(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(Request(
                request_id=row["request_id"].strip().upper(),
                pool=clean_id(row["pool"]),
                client_id=clean_id(row["client_id"]),
                arrival_ms=parse_ms(row["arrival"]),
                duration_ms=parse_ms(row["duration"]) or DEFAULT_DURATION_MS,
            ))
    return sorted(rows, key=lambda r: r.arrival_ms)


def load_probes(path):
    probes = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            probes.append(Probe(
                backend_id=clean_id(row["backend_id"]),
                at_ms=parse_ms(row["at"]),
                healthy=bool(row["healthy"].strip()),
            ))
    return sorted(probes, key=lambda p: p.at_ms)
