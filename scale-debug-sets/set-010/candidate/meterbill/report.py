from pathlib import Path

from .billing import invoice
from .config import load_config
from .limiter import replay
from .loader import load_requests, load_usage
from .usage import by_endpoint, monthly_tokens

DATA = Path(__file__).resolve().parent.parent / "data"


def top_tenants(invoices, n=3):
    ranked = sorted(invoices.items(), key=lambda kv: (kv[1]["total"], kv[0]))
    return [tid for tid, _ in ranked[:n]]


def build_report(data_dir=DATA):
    data_dir = Path(data_dir)
    period, tenants = load_config(data_dir / "config.json")
    throttled = replay(load_requests(data_dir / "requests.csv"), tenants)
    usage = load_usage(data_dir / "usage.csv")
    tokens = monthly_tokens(usage, period)
    invoices = {tid: invoice(t, tokens.get(tid, 0)) for tid, t in sorted(tenants.items())}
    return {
        "throttle": {"throttled": sorted(throttled), "retry_after_s": throttled},
        "usage": {"monthly_tokens": dict(sorted(tokens.items())), "by_endpoint": by_endpoint(usage, period)},
        "invoices": invoices,
        "top_tenants": top_tenants(invoices),
    }
