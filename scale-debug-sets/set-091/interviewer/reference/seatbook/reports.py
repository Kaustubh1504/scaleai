from collections import Counter
from pathlib import Path

from .allocation import allocate
from .holds import split_holds
from .loader import load_holds, load_members, load_sessions

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(sessions, results):
    capacity = Counter({sid: s.capacity for sid, s in sessions.items()})
    booked = Counter({sid: r.seats_booked for sid, r in results.items()})
    seats_left = {sid: capacity[sid] - booked[sid] for sid in sorted(capacity)}

    per_member = Counter()
    for result in results.values():
        for hold in result.booked:
            per_member[hold.member_id] += hold.seats
    top = min(per_member, key=lambda m: (-per_member[m], m)) if per_member else None

    total_capacity = sum(capacity.values())
    total_booked = sum(booked.values())
    return {
        "seats_left": seats_left,
        "total_booked": total_booked,
        "fill_rate": round(total_booked / total_capacity, 3) if total_capacity else 0.0,
        "top_member": top,
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    sessions = load_sessions(data_dir / "sessions.csv")
    members = load_members(data_dir / "members.csv")
    holds = load_holds(data_dir / "holds.csv", sessions, members)
    live, expired = split_holds(holds)
    results = allocate(sessions, live, members)
    return {
        "sessions": {
            sid: {
                "booked": sorted(h.hold_id for h in r.booked),
                "waitlist": sorted(h.hold_id for h in r.waitlist),
                "seats_booked": r.seats_booked,
            }
            for sid, r in results.items()
        },
        "expired": sorted(h.hold_id for h in expired),
        "summary": summarize(sessions, results),
    }
