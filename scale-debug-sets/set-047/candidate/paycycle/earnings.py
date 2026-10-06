from collections import defaultdict


def in_period(ts, period):
    return period["start"] <= ts <= period["end"]


def base_earnings(tasks, rates, period):
    totals = defaultdict(int)
    seen = set()
    for task in tasks:
        if task["task_id"] in seen:
            continue
        seen.add(task["task_id"])
        if task["status"] != "approved" or task["task_type"] not in rates:
            continue
        if not in_period(task["completed_at"], period):
            continue
        totals[task["contributor_id"]] += rates[task["task_type"]]
    return dict(totals)


def bonus_totals(bonuses):
    totals = defaultdict(int)
    for bonus in bonuses:
        totals[bonus["contributor_id"]] += bonus["amount_cents"]
    return dict(totals)
