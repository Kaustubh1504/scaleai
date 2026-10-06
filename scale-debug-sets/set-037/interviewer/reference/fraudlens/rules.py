from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import timedelta

from .money import to_usd

VELOCITY_WINDOW = timedelta(minutes=10)
VELOCITY_COUNT = 3
WEIGHTS = {"velocity": 40, "foreign": 30, "over_limit": 50}
BLOCK_AT = 70
REVIEW_AT = 40


@dataclass
class CardState:
    recent: deque = field(default_factory=deque)
    spend_by_day: dict = field(default_factory=lambda: defaultdict(float))


def action_for(score):
    if score >= BLOCK_AT:
        return "block"
    if score >= REVIEW_AT:
        return "review"
    return "allow"


def velocity_hit(state, ts):
    while state.recent and ts - state.recent[0] > VELOCITY_WINDOW:
        state.recent.popleft()
    state.recent.append(ts)
    return len(state.recent) >= VELOCITY_COUNT


def evaluate(txn, card, state, rates):
    """Flags for one transaction; updates the card's running state."""
    usd = to_usd(txn.amount, txn.currency, rates)
    flags = []
    if velocity_hit(state, txn.ts):
        flags.append("velocity")
    if card is not None and txn.country and txn.country != card.home_country:
        flags.append("foreign")
    day = txn.ts.date()
    state.spend_by_day[day] += usd
    if card is not None and state.spend_by_day[day] > card.daily_limit_usd:
        flags.append("over_limit")
    return usd, flags
