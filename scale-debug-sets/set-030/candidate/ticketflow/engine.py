from .workflow import find_transition, has_transition


# VERIFIED
def ordered(events):
    """Events by timestamp; `seq` breaks ties because the export is not in order."""
    return sorted(events, key=lambda e: (e.ts, e.seq))


class Replay:
    def __init__(self, tickets, people, transitions):
        self.tickets = tickets
        self.people = people
        self.transitions = transitions
        self.rejected = []

    def reject(self, event, reason):
        self.rejected.append([event.ts.strftime("%H:%M"), event.ticket_id, event.actor, event.action, reason])

    def apply(self, event):
        ticket = self.tickets.get(event.ticket_id)
        if ticket is None:
            return self.reject(event, "unknown_ticket")
        if event.action == "tag":
            if ticket.state == "closed":
                return self.reject(event, "invalid_transition")
            if event.value not in ticket.labels:
                ticket.labels.append(event.value)
            return None
        role = self.people.get(event.actor)
        transition = find_transition(self.transitions, ticket.state, event.action, role)
        if transition is None:
            known = has_transition(self.transitions, ticket.state, event.action)
            return self.reject(event, "role_not_allowed" if known else "invalid_transition")
        ticket.state = transition.target
        ticket.updated_at = event.ts
        if transition.counts_as_response and ticket.first_response is None:
            ticket.first_response = event.ts
        return None

    def run(self, events):
        for event in ordered(events):
            self.apply(event)
        return self
