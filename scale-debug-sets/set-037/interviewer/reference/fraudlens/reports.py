from pathlib import Path

from .engine import score_all
from .loader import load_cards, load_rates, load_transactions

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    txns, rejected = load_transactions(data_dir / "transactions.csv")
    cards = load_cards(data_dir / "cards.json")
    rates = load_rates(data_dir / "rates.json")
    decisions = score_all(txns, cards, rates)
    blocked = sorted(d.txn_id for d in decisions.values() if d.action == "block")
    return {
        "decisions": {tid: {"card": d.card_id, "usd": d.usd, "score": d.score, "flags": d.flags, "action": d.action}
                      for tid, d in decisions.items()},
        "rejected": rejected,
        "summary": {
            "loaded": len(txns),
            "rejected": len(rejected),
            "total_usd": round(sum(d.usd for d in decisions.values() if d.usd is not None), 2),
            "blocked": blocked,
        },
    }
