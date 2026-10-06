import csv

from .models import Event, Seat
from .utils import clean, norm_id, parse_time


def load_seats(path):
    seats = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            seat = Seat(norm_id(row["seat_id"]), clean(row["section"]).upper(), float(clean(row["price"])))
            seats[seat.seat_id] = seat
    return seats


def load_events(path):
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for seq, row in enumerate(csv.DictReader(fh)):
            events.append(Event(
                seq=seq,
                event_id=clean(row["event_id"]),
                at=parse_time(row["at"]),
                customer=norm_id(row["customer"]),
                action=clean(row["action"]).lower(),
                seat_id=norm_id(row["seat"]),
            ))
    return events
