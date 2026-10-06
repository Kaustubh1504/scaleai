from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Plan(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class PlanTerms:
    plan: Plan
    rpm: int
    included_units: int
    price_per_1k_cents: int
    base_cents: int


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    name: str
    plan: Plan
    active: bool
    rpm_override: int | None = None


@dataclass(frozen=True)
class Event:
    tenant_id: str
    ts: datetime
    endpoint: str
    units: int
