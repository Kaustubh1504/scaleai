import csv
import json
import re

from .models import Backend, HealthCheck, Request

YES = {"yes", "y", "true", "1"}
OFFSET_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(ms|s)?$")


def clean(value):
    return str(value if value is not None else "").strip()


# VERIFIED
def parse_offset(value):
    """'1.25s', '1250ms' or a bare number of milliseconds -> integer milliseconds."""
    match = OFFSET_RE.match(clean(value).lower())
    if not match:
        raise ValueError(f"unrecognised offset: {value!r}")
    amount, unit = float(match.group(1)), match.group(2)
    if unit == "s":
        amount *= 1000
    return int(round(amount))


def norm(value):
    return clean(value).lower()


def parse_flag(value):
    return bool(norm(value))


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_backends(path, pool):
    """Enabled backends of one pool, keyed by id."""
    backends = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if norm(row["pool"]) != pool or not parse_flag(row["enabled"]):
                continue
            bid = norm(row["backend_id"])
            backends[bid] = Backend(bid, norm(row["zone"]), int(row["weight"]), int(row["max_conns"]))
    return backends


def load_health(path):
    with open(path, newline="", encoding="utf-8") as fh:
        checks = [HealthCheck(parse_offset(r["t"]), norm(r["backend_id"]), norm(r["result"]) == "pass")
                  for r in csv.DictReader(fh)]
    return sorted(checks, key=lambda c: c.t_ms)


def load_requests(path):
    with open(path, newline="", encoding="utf-8") as fh:
        reqs = [Request(clean(r["request_id"]).upper(), parse_offset(r["t"]), norm(r["session"]),
                        int(clean(r["duration_ms"])))
                for r in csv.DictReader(fh)]
    return sorted(reqs, key=lambda r: (r.t_ms, r.id))
