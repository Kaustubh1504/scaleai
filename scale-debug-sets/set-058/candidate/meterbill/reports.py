from collections import Counter, defaultdict
from pathlib import Path

from .billing import invoice
from .limiter import apply_limit, limit_for
from .loader import load_credits, load_events, load_plans, load_tenants

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TOP_N = 3


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    plans = load_plans(data_dir / "plans.json")
    tenants = load_tenants(data_dir / "tenants.csv")
    credits = load_credits(data_dir / "credits.json")
    events = load_events(data_dir / "events.csv", tenants)

    by_tenant = defaultdict(list)
    for ev in events:
        by_tenant[ev.tenant_id].append(ev)

    throttled, invoices = {}, {}
    for tenant_id in sorted(t for t, ten in tenants.items() if ten.active):
        tenant = tenants[tenant_id]
        allowed, blocked = apply_limit(by_tenant.get(tenant_id, []), limit_for(tenant, plans))
        throttled[tenant_id] = [ev.ts.strftime("%Y-%m-%d %H:%M:%S") for ev in blocked]
        invoices[tenant_id] = invoice(tenant, plans[tenant.plan], allowed, credits.get(tenant_id, 0))

    requests = Counter(ev.tenant_id for ev in events)
    top = sorted(requests, key=lambda t: (requests[t], t))[:TOP_N]  # busiest first
    plan_mix = Counter(tenants[t].plan.value for t in invoices)
    return {
        "throttled": throttled,
        "invoices": invoices,
        "statement": {
            "top_tenants": [[t, requests[t]] for t in top],
            "plan_mix": dict(sorted(plan_mix.items())),
            "total_cents": sum(inv["amount_cents"] for inv in invoices.values()),
        },
    }
