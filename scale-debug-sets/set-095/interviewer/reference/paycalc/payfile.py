from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .audit import audit_flags
from .earnings import build_statements, payable_entries
from .loader import load_adjustments, load_contributors, load_period, load_rates, load_work

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def payout_lines(statements, contributors):
    paid = [contributors[cid] for cid, s in statements.items() if s.status == "paid"]
    paid.sort(key=lambda c: c.account_no)
    return [f"{c.account_no},{c.method},{statements[c.contributor_id].net}" for c in paid]


def summarize(statements, contributors):
    by_method = defaultdict(Decimal)
    for cid, s in statements.items():
        if s.status == "paid":
            by_method[contributors[cid].method] += s.net
    return {
        "paid": sum(s.status == "paid" for s in statements.values()),
        "held": sum(s.status == "held" for s in statements.values()),
        "totals_by_method": {m: str(v) for m, v in sorted(by_method.items())},
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    period = load_period(data_dir / "period.json")
    contributors = load_contributors(data_dir / "contributors.csv")
    rates = load_rates(data_dir / "rates.csv")
    work = load_work(data_dir / "work_log.csv")
    entries = payable_entries(work, contributors, rates, period)
    statements = build_statements(entries, contributors, rates, load_adjustments(data_dir / "adjustments.json"), period)
    return {
        "statements": {
            cid: {"tasks": s.tasks, "gross": str(s.gross), "adjustments": str(s.adjustments),
                  "net": str(s.net), "status": s.status}
            for cid, s in statements.items()
        },
        "flags": audit_flags(entries, rates),
        "payout_file": payout_lines(statements, contributors),
        "summary": summarize(statements, contributors),
    }
