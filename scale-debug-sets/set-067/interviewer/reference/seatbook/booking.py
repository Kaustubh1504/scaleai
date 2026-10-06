from .models import Hold

HOLD_TTL_S = 15 * 60


# VERIFIED
def best_available(seats, section, quantity):
    """Lowest row first, then lowest seat number. None if the section can't fit the party."""
    free = sorted((s for s in seats if s.section == section and s.status == "available"),
                  key=lambda s: (s.row, s.number))
    if len(free) < quantity:
        return None
    return free[:quantity]


class Venue:
    def __init__(self, seats):
        self.seats = seats
        self.holds = {}       # customer -> active Hold
        self.statuses = {}    # request_id -> outcome
        self.held_seats = {}  # request_id -> seat labels granted by a hold

    def expire(self, now):
        for customer, hold in list(self.holds.items()):
            age = (now - hold.held_at).total_seconds()
            if age >= HOLD_TTL_S:
                self._free(hold)
                del self.holds[customer]

    def _free(self, hold):
        for seat in hold.seats:
            seat.status, seat.holder = "available", None

    def _hold(self, req):
        if req.customer in self.holds:
            return "duplicate"
        picked = best_available(self.seats, req.section, req.quantity)
        if picked is None:
            return "rejected"
        for seat in picked:
            seat.status, seat.holder = "held", req.customer
        self.holds[req.customer] = Hold(req.request_id, req.customer, req.ts, picked)
        self.held_seats[req.request_id] = [s.label for s in picked]
        return "held"

    def _confirm(self, req):
        hold = self.holds.pop(req.customer, None)
        if hold is None:
            return "no_hold"
        for seat in hold.seats:
            seat.status = "sold"
        return "confirmed"

    def _release(self, req):
        hold = self.holds.pop(req.customer, None)
        if hold is None:
            return "noop"
        self._free(hold)
        return "released"

    def handle(self, req):
        self.expire(req.ts)
        if req.action == "hold":
            status = self._hold(req)
        elif req.action == "confirm":
            status = self._confirm(req)
        elif req.action == "release" or req.action == "cancel":
            status = self._release(req)
        else:
            status = "ignored"
        self.statuses[req.request_id] = status
        return status
