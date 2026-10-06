from pathlib import Path

from .ledger import build_statements
from .loader import load_adjustments, load_contributors, load_entries, load_rates

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def settle(statement, min_payout):
    gross = statement.gross
    paid = gross if gross >= min_payout else 0
    return paid, gross - paid


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    rates = load_rates(data_dir / "rates.json")
    contributors = load_contributors(data_dir / "contributors.csv")
    entries = load_entries(data_dir / "work_log.csv")
    adjustments = load_adjustments(data_dir / "adjustments.csv")
    statements, unmatched = build_statements(contributors, entries, adjustments, rates)

    rows = {}
    for cid, st in statements.items():
        paid, carry = settle(st, rates["min_payout"])
        rows[cid] = {
            "lines": st.lines,
            "earned": st.earned,
            "bonus": st.bonus,
            "clawback": st.clawback,
            "gross": st.gross,
            "paid": paid,
            "carry_forward": carry,
        }
    return {
        "statements": rows,
        "summary": {
            "total_paid": sum(r["paid"] for r in rows.values()),
            "paid_contributors": sorted(cid for cid, r in rows.items() if r["paid"] > 0),
            "held": sorted(cid for cid, r in rows.items() if r["paid"] == 0),
            "unmatched_adjustments": unmatched,
        },
    }
