from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


@dataclass
class Statement:
    contributor_id: str
    tasks: int
    gross: Decimal
    adjustments: Decimal
    net: Decimal
    status: str


# VERIFIED
def in_period(entry, period):
    return period.start <= entry.submitted_at.date() < period.end


def payable_entries(work, contributors, rates, period):
    return [
        e for e in work
        if e.status == "approved" and e.contributor_id in contributors and e.project in rates and in_period(e, period)
    ]


def to_cents(amount):
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def build_statements(entries, contributors, rates, adjustments, period):
    gross = defaultdict(Decimal)
    tasks = defaultdict(int)
    for e in entries:
        gross[e.contributor_id] += rates[e.project].per_task
        tasks[e.contributor_id] += 1
    adjusted = defaultdict(Decimal)
    for cid, amount in adjustments:
        adjusted[cid] += amount

    statements = {}
    for cid in sorted(contributors):
        net = to_cents(gross[cid] + adjusted[cid])
        status = "paid" if net >= period.minimum_payout else "held"
        statements[cid] = Statement(cid, tasks[cid], to_cents(gross[cid]), to_cents(adjusted[cid]), net, status)
    return statements
