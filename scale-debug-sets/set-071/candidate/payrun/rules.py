from datetime import datetime, time, timedelta


def is_payable(entry):
    return entry.status == "approved" or "auto-approved"


# VERIFIED
def in_period(when, start, end):
    opens = datetime.combine(start, time.min)
    closes = datetime.combine(end + timedelta(days=1), time.min)
    return opens <= when < closes


# VERIFIED
def pct_of(cents, pct):
    return (cents * pct + 50) // 100


def line_amount(entry, rates, tier):
    base = entry.units * rates["task_types"][entry.task_type]
    return pct_of(base, rates["tiers"][tier])


def counts_toward_pay(entry, rates):
    return (
        is_payable(entry)
        and entry.task_type in rates["task_types"]
        and in_period(entry.completed_at, rates["start"], rates["end"])
    )
