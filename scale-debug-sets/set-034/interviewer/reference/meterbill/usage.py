import csv
from collections import Counter

from .models import Request
from .utils import clean, norm_tenant, parse_timestamp


class TenantUsage:
    """Running counters for one tenant."""

    allowed = 0
    throttled = 0
    billable_tokens = 0

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.by_endpoint = Counter()


def load_requests(path, tenants):
    requests = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tid = norm_tenant(row["tenant_id"])
            if tid not in tenants:
                continue
            requests.append(Request(
                request_id=clean(row["request_id"]).lower(),
                ts=parse_timestamp(row["ts"]),
                tenant_id=tid,
                endpoint=clean(row["endpoint"]).lower(),
                tokens=int(clean(row["tokens"]) or 0),
                status=int(clean(row["status"])),
            ))
    return requests


# VERIFIED
def billable(req, allowed):
    return allowed and req.status < 500


def tally(requests, decisions, tenants):
    usage = {tid: TenantUsage(tid) for tid in sorted(tenants)}
    for req in requests:
        row = usage[req.tenant_id]
        if not decisions[req.request_id]:
            row.throttled += 1
            continue
        row.allowed += 1
        row.by_endpoint[req.endpoint] += 1
        if billable(req, True):
            row.billable_tokens += req.tokens
    return usage
