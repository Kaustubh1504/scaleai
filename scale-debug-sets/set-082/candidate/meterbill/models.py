from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Tier:
    up_to_blocks: int | None
    cents_per_block: int


@dataclass(frozen=True)
class Plan:
    name: str
    limit: int
    window_s: int
    billed: bool
    monthly_fee_cents: int
    included_units: int
    tiers: tuple[Tier, ...]


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    plan: str
    rate_override: str
    discount_pct: Decimal


@dataclass(frozen=True)
class Request:
    request_id: str
    tenant_id: str
    ts: datetime
    units: int


@dataclass(frozen=True)
class Credit:
    credit_id: str
    tenant_id: str
    month: str
    amount_cents: int


@dataclass
class Invoice:
    tenant_id: str
    month: str
    usage_units: int = 0
    subtotal_cents: int = 0
    total_cents: int = 0
    credits_cents: int = 0
    credit_ids: list = field(default_factory=list)

    @property
    def key(self):
        return f"{self.tenant_id}/{self.month}"

    @property
    def due_cents(self):
        return self.total_cents - self.credits_cents
