SLA_MINUTES = {1: 30, 2: 120, 3: 480}


def sla_minutes(ticket):
    limit = SLA_MINUTES[ticket.severity]
    return limit / 2 if ticket.vip else limit


def response_minutes(ticket):
    if ticket.first_response is None:
        return None
    return round((ticket.first_response - ticket.opened_at).total_seconds() / 60, 1)


def breached(ticket, as_of):
    """A ticket breaches when its first response (or, without one, as_of) is past the SLA."""
    end = ticket.first_response or as_of
    waited = (end - ticket.opened_at).total_seconds() / 60
    return waited >= sla_minutes(ticket)


def breaches(tickets, as_of):
    return sorted(t.ticket_id for t in tickets.values() if breached(t, as_of))
