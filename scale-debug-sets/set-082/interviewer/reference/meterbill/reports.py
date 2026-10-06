from pathlib import Path

from .credits import apply_credits
from .invoices import build_invoices
from .limiter import replay
from .loader import load_credits, load_plans, load_requests, load_tenants
from .plans import effective_limit

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    plans = load_plans(data_dir / "plans.json")
    tenants = load_tenants(data_dir / "tenants.csv")
    requests, skipped = load_requests(data_dir / "requests.csv", tenants)
    limits = {tid: effective_limit(t, plans[t.plan]) for tid, t in tenants.items()}
    accepted, rejected, timeline = replay(requests, limits)
    invoices = build_invoices(accepted, tenants, plans)
    unapplied = apply_credits(invoices, load_credits(data_dir / "credits.json"))
    return {
        "skipped": skipped,
        "tenants": {tid: {"plan": t.plan, "discount_pct": str(t.discount_pct)} for tid, t in sorted(tenants.items())},
        "limits": {tid: list(limit) for tid, limit in sorted(limits.items())},
        "timeline": timeline,
        "rejected": dict(sorted(rejected.items())),
        "invoices": {
            inv.key: {
                "usage_units": inv.usage_units,
                "subtotal_cents": inv.subtotal_cents,
                "total_cents": inv.total_cents,
                "credits_cents": inv.credits_cents,
                "due_cents": inv.due_cents,
            }
            for inv in sorted(invoices.values(), key=lambda i: i.key)
        },
        "unapplied_credits": unapplied,
    }
