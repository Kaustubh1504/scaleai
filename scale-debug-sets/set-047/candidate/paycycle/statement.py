from pathlib import Path

from .earnings import base_earnings, bonus_totals
from .loader import load_bonuses, load_period, load_rates, load_tasks

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def platform_fee(gross_cents, fee_percent):
    return round(gross_cents * fee_percent / 100)


def build_statement(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    period = load_period(data_dir / "period.json")
    base = base_earnings(load_tasks(data_dir / "tasks.csv"), load_rates(data_dir / "rates.csv"), period)
    bonus = bonus_totals(load_bonuses(data_dir / "bonuses.csv"))
    lines = {}
    for cid in sorted(set(base) | set(bonus)):
        gross = base.get(cid, 0) + bonus.get(cid, 0)
        fee = platform_fee(gross, period["fee_percent"])
        net = gross - fee
        lines[cid] = {
            "base_cents": base.get(cid, 0),
            "bonus_cents": bonus.get(cid, 0),
            "gross_cents": gross,
            "fee_cents": fee,
            "net_cents": net,
            "status": "paid" if net >= period["min_payout_cents"] else "carried_over",
        }
    paid = [cid for cid, line in lines.items() if line["status"] == "paid"]
    return {
        "lines": lines,
        "paid": paid,
        "carried_over": [cid for cid in lines if cid not in paid],
        "total_paid_cents": sum(lines[cid]["net_cents"] for cid in paid),
    }
