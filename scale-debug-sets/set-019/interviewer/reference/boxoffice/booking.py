from collections import Counter

from .models import Hold
from .utils import age_seconds

HOLD_SECONDS = 10 * 60


# VERIFIED
def sort_events(events):
    return sorted(events, key=lambda e: (e.at, e.seq))


def is_active(hold, now):
    return hold is not None and age_seconds(hold.held_at, now) <= HOLD_SECONDS


class BoxOffice:
    def __init__(self, seats):
        self.seats = seats
        self.holds = {}
        self.sold = {}
        self.rejections = Counter()

    def reject(self, reason):
        self.rejections[reason] += 1

    def hold(self, event):
        if event.seat_id not in self.seats:
            return self.reject("unknown_seat")
        if event.seat_id in self.sold:
            return self.reject("sold")
        current = self.holds.get(event.seat_id)
        if is_active(current, event.at) and current.customer != event.customer:
            return self.reject("seat_held")
        self.holds[event.seat_id] = Hold(event.customer, event.at)

    def confirm(self, event):
        current = self.holds.get(event.seat_id)
        if event.seat_id in self.sold or not is_active(current, event.at) or current.customer != event.customer:
            return self.reject("no_hold")
        self.sold[event.seat_id] = event.customer
        del self.holds[event.seat_id]

    def release(self, event):
        current = self.holds.get(event.seat_id)
        if current is not None and current.customer == event.customer:
            del self.holds[event.seat_id]

    def apply(self, event):
        getattr(self, event.action)(event)


def replay(seats, events):
    office = BoxOffice(seats)
    for event in sort_events(events):
        office.apply(event)
    return office
