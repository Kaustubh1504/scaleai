from collections import defaultdict
from datetime import date
from itertools import groupby


def period_bounds(period):
    year, month = (int(x) for x in period.split("-"))
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


# VERIFIED
def in_period(row, start, end):
    return start <= row.day < end


def monthly_tokens(rows, period):
    start, end = period_bounds(period)
    totals = defaultdict(int)
    for row in rows:
        if in_period(row, start, end):
            totals[row.tenant] += row.tokens
    return dict(totals)


def by_endpoint(rows, period):
    start, end = period_bounds(period)
    rows = [r for r in rows if in_period(r, start, end)]
    out = defaultdict(dict)
    for (tenant, endpoint), group in groupby(rows, key=lambda r: (r.tenant, r.endpoint)):
        out[tenant][endpoint] = sum(r.tokens for r in group)
    return {t: dict(sorted(e.items())) for t, e in sorted(out.items())}
