import csv
import json
from decimal import Decimal

from .models import Plan, Tenant
from .utils import clean, norm_tenant


def load_plans(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        name.strip().lower(): Plan(
            name=name.strip().lower(),
            limit=int(spec["limit"]),
            window=int(spec["window_ms"]) / 1000,
            price_per_1k=Decimal(str(spec["price_per_1k"])),
            included_tokens=int(spec["included_tokens"]),
        )
        for name, spec in raw.items()
    }


def effective_limit(override, plan):
    text = clean(override)
    override = int(text) if text else None
    return plan.limit if override is None else override


def load_tenants(path, plans):
    tenants = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tid = norm_tenant(row["tenant_id"])
            plan = plans[clean(row["plan"]).lower()]
            tenants[tid] = Tenant(tid, plan, effective_limit(row["limit_override"], plan))
    return tenants
