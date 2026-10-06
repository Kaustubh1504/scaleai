from datetime import timedelta

HOLD_MINUTES = 15


def is_confirmed(hold):
    if hold.confirmed_at is None:
        return False
    deadline = hold.placed_at + timedelta(minutes=HOLD_MINUTES)
    return hold.confirmed_at <= deadline


def split_holds(holds):
    """Return (live, expired) where live holds were confirmed inside the window."""
    live, expired = [], []
    for hold in holds:
        (live if is_confirmed(hold) else expired).append(hold)
    return live, expired
