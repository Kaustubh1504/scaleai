from .models import Booking, Hold

HOLD_SECONDS = 10 * 60
OCCUPYING = ("confirmed", "comped")


def is_expired(hold, now):
    return (now - hold.held_at).seconds > HOLD_SECONDS


class Ledger:
    def __init__(self, sessions):
        self.sessions = sessions
        self.holds = {}      # (session_id, attendee) -> Hold
        self.bookings = []
        self.outcomes = {}   # event id -> "ok" or a rejection reason

    def taken(self, session_id):
        return sum(b.seats for b in self.bookings if b.session_id == session_id and b.status in OCCUPYING)

    def held(self, session_id, now):
        return sum(h.seats for (sid, _), h in self.holds.items() if sid == session_id and not is_expired(h, now))

    # VERIFIED
    def has_room(self, session_id, seats, now):
        left = self.sessions[session_id].capacity - self.taken(session_id) - self.held(session_id, now)
        return left - seats >= 0

    def active_booking(self, session_id, attendee):
        for b in self.bookings:
            if b.session_id == session_id and b.attendee == attendee and b.status in OCCUPYING:
                return b
        return None

    def hold(self, ev):
        key = (ev.session_id, ev.attendee)
        current = self.holds.get(key)
        if current is not None and not is_expired(current, ev.at) or self.active_booking(*key):
            return "duplicate"
        if not self.has_room(ev.session_id, ev.seats, ev.at):
            return "full"
        self.holds[key] = Hold(ev.attendee, ev.seats, ev.at)
        return "ok"

    def confirm(self, ev):
        hold = self.holds.pop((ev.session_id, ev.attendee), None)
        if hold is None:
            return "no_hold"
        if is_expired(hold, ev.at):
            return "expired"
        self.bookings.append(Booking(ev.session_id, ev.attendee, hold.seats, "confirmed"))
        return "ok"

    def cancel(self, ev):
        booking = self.active_booking(ev.session_id, ev.attendee)
        if booking is not None:
            booking.status = "cancelled"
            return "ok"
        hold = self.holds.pop((ev.session_id, ev.attendee), None)
        if hold is not None and not is_expired(hold, ev.at):
            return "ok"
        return "nothing_to_cancel"

    def comp(self, ev):
        if not self.has_room(ev.session_id, ev.seats, ev.at):
            return "full"
        self.bookings.append(Booking(ev.session_id, ev.attendee, ev.seats, "comped"))
        return "ok"

    def apply(self, ev):
        session = self.sessions.get(ev.session_id)
        if session is None:
            outcome = "unknown_session"
        elif ev.action in ("hold", "comp") and ev.at >= session.starts_at:
            outcome = "closed"
        else:
            outcome = getattr(self, ev.action)(ev)
        self.outcomes[ev.id] = outcome
        return outcome


def replay(sessions, events):
    ledger = Ledger(sessions)
    for ev in events:
        ledger.apply(ev)
    return ledger
