# 45. Audit log and metrics
# Standalone: copy this file as-is. Deps: stdlib

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

_audit_lock = threading.Lock()


def audit_log(path, event: str, **fields) -> None:
    """Append one JSON line: {"ts", "event", ...fields}. Append-only; never rewrite history."""
    line = json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields},
                      ensure_ascii=False, default=str)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with _audit_lock, open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def new_metrics() -> dict:
    return {"counts": {}, "timings": {}, "lock": threading.Lock()}


def inc(metrics: dict, name: str, n: int = 1) -> None:
    with metrics["lock"]:
        metrics["counts"][name] = metrics["counts"].get(name, 0) + n


@contextmanager
def timed(metrics: dict, name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - start) * 1000
        with metrics["lock"]:
            metrics["timings"].setdefault(name, []).append(ms)


def snapshot(metrics: dict) -> dict:
    """{"counts": {...}, "timings": {name: {"count", "p50_ms", "p95_ms", "max_ms"}}}: serve at GET /metrics."""
    def pct(values, p):
        return round(values[min(len(values) - 1, int(round(p * (len(values) - 1))))], 2)

    with metrics["lock"]:
        timings = {k: sorted(v) for k, v in metrics["timings"].items()}
        counts = dict(metrics["counts"])
    return {"counts": counts,
            "timings": {k: {"count": len(v), "p50_ms": pct(v, 0.5), "p95_ms": pct(v, 0.95),
                            "max_ms": round(v[-1], 2)} for k, v in timings.items() if v}}
