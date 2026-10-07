import json
from datetime import date, datetime


def _encode(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def export_roster(roster):
    """The roster as a JSON list sorted by email, as written to roster.json."""
    rows = [vars(c) for _, c in sorted(roster.items())]
    return json.dumps(rows, default=_encode, indent=2, sort_keys=True)
