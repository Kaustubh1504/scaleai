from pathlib import Path

from .billing import invoice, total
from .limiter import run
from .plans import load_plans, load_tenants
from .usage import load_requests, tally

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    plans = load_plans(data_dir / "plans.json")
    tenants = load_tenants(data_dir / "tenants.csv", plans)
    requests = load_requests(data_dir / "requests.csv", tenants)
    decisions = run(requests, tenants)
    usage = tally(requests, decisions, tenants)
    invoices = {tid: invoice(usage[tid], tenants[tid]) for tid in sorted(tenants)}
    top = sorted(invoices, key=lambda tid: (-invoices[tid]["amount"], tid))[:3]
    return {
        "limits": {tid: t.limit for tid, t in sorted(tenants.items())},
        "throttled": {tid: sorted(r.request_id for r in requests if r.tenant_id == tid and not decisions[r.request_id])
                      for tid in sorted(tenants)},
        "usage": {
            tid: {
                "allowed": u.allowed,
                "throttled": u.throttled,
                "billable_tokens": u.billable_tokens,
                "by_endpoint": dict(sorted(u.by_endpoint.items())),
            }
            for tid, u in usage.items()
        },
        "invoices": {tid: {**inv, "amount": str(inv["amount"])} for tid, inv in invoices.items()},
        "total": str(total(invoices)),
        "top_tenants": top,
    }
