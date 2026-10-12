"""23. Latest record wins (CDC stream): reference solution."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

FMT = "%Y-%m-%dT%H:%M:%SZ"


def _utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def materialize(events: list[dict]) -> tuple[list[dict], list[dict]]:
    best: dict[str, tuple[tuple, dict]] = {}  # id -> ((instant, version), event)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for ev in events:
        at = _utc(ev["updated_at"])
        key = (at, ev["version"])
        if ev["id"] not in best or key >= best[ev["id"]][0]:  # >=: a later exact tie wins
            best[ev["id"]] = (key, ev)
        content = {k: v for k, v in ev.items() if k != "updated_at"}
        content["deleted"] = bool(ev.get("deleted"))
        groups[(ev["id"], at, ev["version"])].append(content)

    records = []
    for rid, ((at, _), ev) in sorted(best.items()):
        if not ev.get("deleted"):
            out = {k: v for k, v in ev.items() if k != "deleted"}
            out["updated_at"] = at.strftime(FMT)
            records.append(out)

    conflicts = [{"id": rid, "version": version, "updated_at": at.strftime(FMT)}
                 for (rid, at, version), bodies in sorted(groups.items())
                 if any(b != bodies[0] for b in bodies)]
    return records, conflicts


if __name__ == "__main__":
    from problem_api import STREAM

    records, conflicts = materialize(STREAM)
    for r in records:
        print(r)
    print("conflicts:", conflicts)
