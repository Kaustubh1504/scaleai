"""Tenant and plan configuration, validated once at startup."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    burst: float
    refill_per_s: float


@dataclass(frozen=True)
class TenantConfig:
    plans: dict[str, Plan]
    tenant_plans: dict[str, str]

    def plan_for(self, tenant_id: str) -> Plan | None:
        name = self.tenant_plans.get(tenant_id)
        return self.plans[name] if name is not None else None


def parse_config(raw: dict) -> TenantConfig:
    """Fail fast on a bad config instead of on the first request that hits it."""
    plans = {}
    for name, spec in raw["plans"].items():
        plan = Plan(burst=float(spec["burst"]), refill_per_s=float(spec["refill_per_s"]))
        if plan.burst < 1 or plan.refill_per_s <= 0:
            raise ValueError(f"plan {name!r}: burst must be >= 1 and refill_per_s > 0")
        plans[name] = plan
    tenant_plans = {}
    for tenant_id, spec in raw["tenants"].items():
        if spec["plan"] not in plans:
            raise ValueError(f"tenant {tenant_id!r} uses unknown plan {spec['plan']!r}")
        tenant_plans[tenant_id] = spec["plan"]
    return TenantConfig(plans, tenant_plans)
