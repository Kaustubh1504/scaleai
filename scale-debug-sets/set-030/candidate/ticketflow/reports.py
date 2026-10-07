import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from .engine import Replay
from .loader import load_events, load_people, load_tickets, parse_ts
from .sla import breaches, response_minutes
from .workflow import load_workflow

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AS_OF = "2026-05-04 18:00"


def actor_activity(events):
    stats = defaultdict(Counter)
    for event in events:
        stats[event.actor].update(event.action)
    return {actor: dict(sorted(counts.items())) for actor, counts in sorted(stats.items())}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    as_of = parse_ts(AS_OF)
    tickets = load_tickets(data_dir / "tickets.csv")
    events = load_events(data_dir / "events.csv")
    replay = Replay(tickets, load_people(data_dir / "people.json"), load_workflow(data_dir / "workflow.json"))
    replay.run(events)
    return {
        "as_of": as_of,
        "tickets": {
            tid: {
                "state": t.state,
                "labels": list(t.labels),
                "first_response_min": response_minutes(t),
                "updated_at": t.updated_at,
            }
            for tid, t in sorted(tickets.items())
        },
        "rejected": replay.rejected,
        "sla_breaches": breaches(tickets, as_of),
        "actors": actor_activity(events),
    }


def _encode(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def to_json(report):
    return json.dumps(report, default=_encode, indent=2)
