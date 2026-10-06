from collections import defaultdict
from dataclasses import dataclass

from .money import UnknownCurrencyError
from .rules import WEIGHTS, CardState, action_for, evaluate

UNKNOWN_CURRENCY_SCORE = 40


@dataclass
class Decision:
    txn_id: str
    card_id: str
    usd: float | None
    score: int
    flags: list
    action: str


def score_all(txns, cards, rates):
    states = defaultdict(CardState)
    decisions = {}
    for txn in txns:
        try:
            usd, flags = evaluate(txn, cards.get(txn.card_id), states[txn.card_id], rates)
        except UnknownCurrencyError as exc:
            decisions[txn.txn_id] = Decision(txn.txn_id, txn.card_id, None, UNKNOWN_CURRENCY_SCORE,
                                             [f"unknown_currency:{exc.currency}"], "review")
            continue
        score = sum(WEIGHTS[f] for f in flags)
        decisions[txn.txn_id] = Decision(txn.txn_id, txn.card_id, usd, score, flags, action_for(score))
    return decisions
