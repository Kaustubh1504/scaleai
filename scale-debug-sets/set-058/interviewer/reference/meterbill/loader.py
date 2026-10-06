import csv
import json
from pathlib import Path

from .models import Event, Plan, PlanTerms, Tenant
from .utils import clean, norm_id, parse_bool, parse_int, parse_ts


def load_plans(path):
    plans = {}
    for name, item in json.loads(Path(path).read_text(encoding="utf-8")).items():
        plan = Plan(norm_id(name))
        plans[plan] = PlanTerms(plan, int(item["rpm"]), int(item["included_units"]),
                                int(item["price_per_1k_cents"]), int(item["base_cents"]))
    return plans


def load_tenants(path):
    tenants = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tenant_id = norm_id(row["tenant_id"])
            tenants[tenant_id] = Tenant(
                tenant_id=tenant_id,
                name=clean(row["name"]),
                plan=Plan(norm_id(row["plan"])),
                active=parse_bool(row["active"]),
                rpm_override=parse_int(row["rpm_override"]),
            )
    return tenants


def load_credits(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {norm_id(k): int(v) for k, v in raw.items()}


def load_events(path, tenants):
    """Events for known, active tenants only."""
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tenant = tenants.get(norm_id(row["tenant_id"]))
            if tenant is None or not tenant.active:
                continue
            events.append(Event(tenant.tenant_id, parse_ts(row["ts"]), clean(row["endpoint"]), int(row["units"])))
    return events
