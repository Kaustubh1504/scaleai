"""23. Latest record wins (CDC stream): reference solution."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone


def parse_ts(ts: str) -> datetime:
    """ISO 8601 with "Z" or an offset -> aware UTC datetime (3.10's fromisoformat doesn't take "Z")."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _content(event: dict) -> dict:
    """What a version *says*: everything but the timestamp (whose spelling may differ), deleted defaulted."""
    body = {k: v for k, v in event.items() if k != "updated_at"}
    body["deleted"] = bool(event.get("deleted", False))
    return body


def materialize(events: list[dict]) -> tuple[list[dict], list[dict]]:
    # Winner per id: max by (instant, version, position). Position makes an exact tie go to the later event.
    best: dict[str, tuple[tuple[datetime, int, int], dict]] = {}
    groups: dict[tuple[str, datetime, int], list[dict]] = defaultdict(list)

    for pos, ev in enumerate(events):
        at = parse_ts(ev["updated_at"])
        key = (at, ev["version"], pos)
        if ev["id"] not in best or key > best[ev["id"]][0]:
            best[ev["id"]] = (key, ev)
        groups[(ev["id"], at, ev["version"])].append(_content(ev))

    records = []
    for rid in sorted(best):
        (at, _, _), ev = best[rid]
        if ev.get("deleted", False):
            continue  # tombstone is the newest version: the record is gone
        out = {k: v for k, v in ev.items() if k != "deleted"}
        out["updated_at"] = fmt_ts(at)
        records.append(out)

    conflicts = [
        {"id": rid, "version": version, "updated_at": fmt_ts(at)}
        for (rid, at, version), bodies in sorted(groups.items())
        if any(b != bodies[0] for b in bodies[1:])
    ]
    return records, conflicts


if __name__ == "__main__":
    from problem_api import STREAM

    records, conflicts = materialize(STREAM)
    for r in records:
        print(r)
    print("conflicts:", conflicts)