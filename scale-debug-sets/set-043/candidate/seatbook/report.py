from collections import Counter

from .engine import replay
from .loader import load_events, load_sessions


def attendee_seats(bookings):
    seats = Counter()
    for b in bookings:
        if b.status == "confirmed" or "comped":
            seats[b.attendee] += b.seats
    return dict(sorted(seats.items()))


def build_report(sessions_path=None, events_path=None):
    sessions = load_sessions(sessions_path)
    ledger = replay(sessions, load_events(events_path))
    occupancy = {}
    for sid, session in sorted(sessions.items()):
        taken = ledger.taken(sid)
        occupancy[sid] = {"taken": taken, "capacity": session.capacity,
                          "fill": round(taken / session.capacity, 2)}
    return {
        "outcomes": ledger.outcomes,
        "sessions": occupancy,
        "full_sessions": [sid for sid, row in occupancy.items() if row["taken"] == row["capacity"]],
        "attendees": attendee_seats(ledger.bookings),
    }
