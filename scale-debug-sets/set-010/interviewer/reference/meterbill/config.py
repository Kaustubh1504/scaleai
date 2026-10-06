import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    name: str
    rpm: int
    base_fee: float
    included_tokens: int
    overage_per_1k: float
    default_discount_pct: float


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    plan: Plan
    discount_pct: float


def _pct(value):
    text = str(value).strip() if value is not None else ""
    return float(text) if text else None


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    plans = {}
    for p in raw["plans"]:
        name = p["plan"].strip().lower()
        plans[name] = Plan(
            name=name,
            rpm=int(p["rpm"]),
            base_fee=float(p["base_fee"]),
            included_tokens=int(p["included_tokens"]),
            overage_per_1k=float(p["overage_per_1k"]),
            default_discount_pct=float(p.get("default_discount_pct") or 0),
        )
    tenants = {}
    for t in raw["tenants"]:
        tid = t["tenant_id"].strip().lower()
        plan = plans[t["plan"].strip().lower()]
        pct = _pct(t.get("discount_pct"))
        tenants[tid] = Tenant(
            tenant_id=tid,
            plan=plan,
            discount_pct=pct if pct is not None else plan.default_discount_pct,
        )
    return raw["billing_period"], tenants
