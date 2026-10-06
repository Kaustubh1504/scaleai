from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Plan:
    name: str
    limit: int
    window: float  # seconds
    price_per_1k: Decimal
    included_tokens: int


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    plan: Plan
    limit: int


@dataclass(frozen=True)
class Request:
    request_id: str
    ts: datetime
    tenant_id: str
    endpoint: str
    tokens: int
    status: int
